from __future__ import annotations

import logging
import asyncio
from dataclasses import dataclass, field
from datetime import datetime

from typing import Any

from src.exceptions import (
    SameUserError,
    AlreadyCLosedDepositPrintError,
    OdooError
)

from src.odoo import OdooConnector
from src.database import ConsigneDatabase
from src.ticket import ConsignePrinter
from src.cache import ConsigneCache, cached_products, cached_shifts, cached_users
from src.utils import generate_ean

tasks_logger = logging.getLogger("tasks")

@dataclass(frozen=True)
class TaskConfigs:
    pooling: bool = field(default=False)
    frequency: int =  field(default=600)



class ConsigneEngine(object):
    odoo: OdooConnector
    database: ConsigneDatabase
    printer: ConsignePrinter
    cache: ConsigneCache
    tasks: dict[str,TaskConfigs]

    def __init__(
        self, 
        odoo: OdooConnector, 
        database: ConsigneDatabase, 
        printer: ConsignePrinter,
        cache: ConsigneCache,
        tasks: dict[str, TaskConfigs] | None = None
    ) -> None:
        self.odoo = odoo
        self.database = database
        self.printer = printer
        self.cache = cache

        if tasks is None:
            tasks = {}
        self.tasks = tasks
        # self.database.load_metadata(__name__)

    def initialize_return(self, receiver_partner_id: int, provider_partner_id: int) -> int:
        """
        for receiver & provider:
            1. fetch users in db
            2. if None, retrieve user data from odoo and build db reference.
            3. provide user_id (db users table pk)
        4. build db reference for the deposit
        Return deposit_id that is need by the front to further operate.
        """
        if receiver_partner_id == provider_partner_id:
            # FORBID OWN RETURNS
            raise SameUserError()

        # search receiver user
        user = self.database.get_user_from_partner_id(receiver_partner_id)
        if user is None:
            # create user when None
            with self.odoo.make_session() as session:
                receiver = session.get_partner_record_from_id(receiver_partner_id)
            res = self.database.add_user(*receiver)
            receiver_user_id = res.get("user_id", None)  
        else:
            receiver_user_id = user.get("user_id", None)
        assert receiver_user_id is not None
        self.database.update_activity(receiver_user_id, "receiver")

        # search provider user
        user = self.database.get_user_from_partner_id(provider_partner_id)
        if user is None:
            # create user when None
            with self.odoo.make_session() as session:
                provider = session.get_partner_record_from_id(provider_partner_id)
            res = self.database.add_user(*provider)
            provider_user_id = res.get("user_id", None)
        else:
            provider_user_id = user.get("user_id", None)
        assert provider_user_id is not None
        self.database.update_activity(provider_user_id, "provider")

        deposit = self.database.add_deposit(receiver_user_id, provider_user_id)
        deposit_id = deposit.get("deposit_id", None)
        assert deposit is not None and isinstance(deposit_id, int)
        return deposit_id
    
    @cached_products
    def fetch_product(self, barcode: str) -> tuple[bool, float, tuple, int]:
        """search propduct in odoo database"""
        with self.odoo.make_session() as session:
            product = session.get_product_from_barcode(barcode)
            product_data = session.product_to_record(product)
            returnable, return_product = session.get_product_return(product)

            return_product_id, return_value = 1, 0.0 # default value = non returnable, 0 return value
            # -- GET RETURN PRODUCT
            if returnable and return_product is not None:
                opid, name, _, return_value = session.product_return_to_record(return_product)
                db_product_return = self.database.get_return_product_from_opid(opid)

                # -- ADD RETURN PRODUCT IF NOT REFERENCED IN THE DATABASE
                if db_product_return is None:
                    db_product_return = self.database.add_product_return(opid, name, returnable, return_value)

                return_product_id = db_product_return.get("product_return_id", None)
                assert return_product_id is not None
            elif returnable and return_product is None:
                raise OdooError(f"Returnable product without return_product: {barcode}")
            
        return (returnable, return_value,  product_data, return_product_id)
                
    
    def return_product(self, deposit_id: int, barcode: str) -> dict[str, Any]:
        """
        1. search for product
        2. define returnability & product_return
        3. update database with product_return & deposit_line
        4. return operation result:
            * success -> returned product data
            * failed -> Non returnable product message.
        """
        returnable, return_value,  product_data, return_product_id = self.fetch_product(barcode)
        # -- SEARCH PRODUCT REFERENCE 
        opid, name, _ = product_data
        db_product = self.database.get_product_from_opid(opid)
        if db_product is None:
            # CREATE PRODUCT REFERENCE
            db_product = self.database.add_product(opid, name, barcode, return_product_id)
        product_id = db_product.get("product_id", None)
        assert product_id is not None

        # -- CREATE DEPOSIT_LINE REFERENCE
        deposit_line = self.database.add_deposit_line(deposit_id, product_id)
        deposit_line_id = deposit_line.get("deposit_line_id")
        return {
            "deposit_line_id": deposit_line_id,
            "product_id": product_id, 
            "odoo_product_id": opid, 
            "name": name,
            "returnable": returnable, 
            "return_value": return_value
        }
        
    def cancel_deposit_line(self, deposit_id: int,  deposit_line_id: int) -> None:
        self.database.cancel_returned_product(deposit_id, deposit_line_id)

    def get_deposit_data(self, deposit_id: int) -> dict[str, Any] | None:
        return self.database.get_deposit_data(deposit_id)

    def get_deposit_line_data(self, deposit_id: int, deposit_line_id: int) -> dict[str, Any] | None:
        return self.database.get_deposit_line_data(deposit_id, deposit_line_id)

    def authenticate_provider(self, username: str, password: str) -> dict[str, Any]:
        """"""
        with self.odoo.make_session() as session:
            auth, user = session.auth_provider(username, password)
            if auth is False:
                return {"auth": auth, "user": None}
            assert user is not None

            oid, code, name = session.user_to_record(user)
            end_shift_dist = session.get_current_shift_end_time_dist()

        db_user = self.database.get_user_from_code(code)
        if db_user is None:
            db_user = self.database.add_user(oid, code, name)

        user_id = db_user.get('user_id', None)
        assert user_id is not None

        self.database.update_activity(user_id, "provider")
        return {"auth": auth, "user": {"user_name": name, "user_code": code, "max_age":end_shift_dist}}
        
    def generate_ticket(self, deposit_id: int) -> None:
        """
        1. collect doposit & deposit_lines data
        2. build aggregated data for quantities and return values
        3. generate ticket
        4. return ticket in the printer accepted format
        """
        
        deposit = self.database.get_deposit_data(deposit_id)
        if deposit is None:
            raise ValueError(f"unknown deposit_id: {deposit_id}")

        if deposit.get("closed", False):
            raise AlreadyCLosedDepositPrintError()

        receiver_id = deposit["deposit"]["receiver_id"]
        ean = deposit["deposit"].get("deposit_barcode", None)
        
        user = self.database.get_user_from_id(receiver_id)
        if user is None:
            raise ValueError(f"Unknown user id: {receiver_id}")
        
        user_code = user["user_code"]
        user_name = user["user_name"]
        receiver = {"user_code": user_code, "user_name": user_name}

        returns_per_types = self.database.get_returns_per_types(deposit_id)
        total_value = sum([r[2] for r in returns_per_types])

        base_id, base = self.database.next_barcode_base()
        if base is None:
            raise ValueError("Next barcode base not found.")

        ean = generate_ean(total_value, base)
        self.database.update_deposit_barcode(deposit_id, ean, base_id)

        with self.printer.make_printer_session() as p:
            p.print_ticket(
                deposit_id=deposit_id,
                **receiver,
                returns_lines=returns_per_types,
                total_value=total_value,
                ean=ean
            )

    @cached_shifts
    def get_shifts_users(self) -> list[tuple[int, int, str]]:
        """get current shift users. return list of barcodebase, display_name"""
        with self.odoo.make_session() as session:
            zone, users = session.get_current_shifts_members()
        return users

    @cached_users
    def search_user(self, value: str) -> list[tuple[int, int, str]]:
        """fuzzy search for the user."""
        with self.odoo.make_session() as session:
            res = session.fuzzy_user_search(value) # list user(id, code, name)
        return res

    def close_deposit(self, deposit_id: int) -> None:
        self.database.close_deposit(deposit_id)

    def redeem_analyzer(self) -> None:
        """
        TODO: analyzer configuration.
        TODO: define search frequency and span.
        """
        before = datetime.now()
        after = self.database.get_last_redeem_datetime() or self.database.get_first_deposit_datetime()

        if after is None:
            return

        bases = self.database.get_tracked_consigne_barcodes_bases()
        with self.odoo.make_session() as session:
            records = session.get_redeemed_tickets(bases, before, datetime.fromisoformat(after))
            for record in records:

                # GET USER & CREATE REFERENCE IF UNKNOWN
                partner = record.order_id.partner_id
                partner_db = self.database.get_user_from_code(partner.barcode_base)
                if partner_db is None:
                    partner_payload = session.get_partner_record_from_code(partner.barcode)
                    partner_db = self.database.add_user(*partner_payload) # use user_id for the redeem record

                user_id = partner_db.get("user_id")
                pos_id, dt, value, barcode =  session.pos_order_line_to_record(record)
                # FIND ALL NON REDEEMED DEPOSITS WITH MATCHING RECEIVER__CODE & DEPOSIT_TOTAL_VALUE
                deposit = self.database.match_redeem_deposits(barcode, user_id, value)
                if deposit:
                    # MATCHING
                    deposit_id = deposit.get("deposit_id")
                    redeem = self.database.add_redeem(pos_id, datetime.fromisoformat(dt), user_id, value, barcode, False)
                    redeem_id = redeem.get("redeem_id")
                    self.database.update_deposit_redeem(deposit_id, redeem_id)
                else:
                    # NO MATCH = ANOMALY
                    self.database.add_redeem(pos_id, datetime.fromisoformat(dt), user_id, value, barcode, True)

    async def ticket_emissions_analyzer(self) -> None:
        settings = self.tasks.get("analyzer", None)
        if settings is None:
            raise ValueError("Analyzer settings must be set to run the ticket emissions analysis")

        tasks_logger.info("ANALYZER | Thread starting...")
        while True:
            tasks_logger.info(f"ANALYZER | Next process in {settings.frequency} secs")
            await asyncio.sleep(settings.frequency)
            self.redeem_analyzer()

    async def bases_tracker_runner(self) -> None:
        settings = self.tasks.get("tracking", None)
        if settings is None:
            raise ValueError("trackinh settings must be set to run the consigne barcode tracking")
        
        tasks_logger.info("TRACKING | Thread starting...")
        while True:
            tasks_logger.info(f"TRACKING | Next process in {settings.frequency} secs")
            await asyncio.sleep(settings.frequency)
            await self.bases_tracker()

    async def bases_tracker(self) -> None:
        with self.odoo.make_session() as session:
            existing = session.get_existing_consigne_barcodes()
        self.database._update_consigne_barcodes(existing)