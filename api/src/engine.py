from __future__ import annotations

from typing import Any

from src.odoo import OdooConnector
from src.database import ConsigneDatabase
from src.ticket import DepositTicket, ConsignePrinter
from src.utils import generate_ean


class ConsigneEngine(object):
    odoo: OdooConnector
    database: ConsigneDatabase
    printer: ConsignePrinter

    def __init__(self, odoo: OdooConnector, database: ConsigneDatabase, printer: ConsignePrinter):
        self.odoo = odoo
        self.database = database
        self.printer = printer

    def initialize_return(self, receiver_code: int, provider_code: int) -> int:
        """
        for receiver & provider:
            1. fetch users in db
            2. if None, retrieve user data from odoo and build db reference.
            3. provide user_id (db users table pk)
        4. build db reference for the deposit
        Return deposit_id that is need by the front to further operate.
        """
        user = self.database.get_user_from_code(receiver_code)
        if user is None:
            with self.odoo.make_session() as session:
                receiver = session.get_partner_record_from_code(receiver_code)
            res = self.database.add_user(*receiver)
            receiver_user_id = res.get("user_id")
            self.database.update_activity(receiver_user_id, "receiver")
        else:
            receiver_user_id = user.get("user_id")

        user = self.database.get_user_from_code(provider_code)
        if user is None:
            with self.odoo.make_session() as session:
                provider = session.get_partner_record_from_code(provider_code)
            res = self.database.add_user(*provider)
            provider_user_id = res.get("user_id")
            self.database.update_activity(provider_user_id, "provider")
        else:
            provider_user_id = user.get("user_id")

        deposit = self.database.add_deposit(receiver_user_id, provider_user_id)
        deposit_id = deposit.get("deposit_id")
        return deposit_id
        
    def return_product(self, deposit_id: int, barcode: str) -> dict[str, Any]:
        """
        1. search for product
        2. define returnability & product_return
        3. update database with product_return & deposit_line
        4. return operation result:
            * success -> returned product data
            * failed -> Non returnable product message.
        """
        with self.odoo.make_session() as session:
            product = session.get_product_from_barcode(barcode)
            product_data = session.product_to_record(product)
            returnable, return_product = session.get_product_return(product)

            return_product_id, return_value = 1, 0.0 # default value = non returnable, 0 return value
            # -- GET RETURN PRODUCT
            if returnable:
                opid, name, _, return_value = session.product_return_to_record(return_product)
                db_product_return = self.database.get_return_product_from_opid(opid)

                # -- ADD RETURN PRODUCT IF NOT REFERENCED IN THE DATABASE
                if db_product_return is None:
                    db_product_return = self.database.add_product_return(opid, name, returnable, return_value)

                return_product_id = db_product_return.get("product_return_id")
                
        # -- SEARCH PRODUCT REFERENCE 
        opid, name, _ = product_data
        db_product = self.database.get_product_from_opid(opid)
        if db_product is None:
            # CREATE PRODUCT REFERENCE
            db_product = self.database.add_product(opid, name, barcode, return_product_id)
        product_id = db_product.get("product_id")
        
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
        self.database.cancel_deposit_line(deposit_id, deposit_line_id)

    def get_deposit_data(self, deposit_id: int) -> dict[str, Any]:
        return self.database.get_deposit_data(deposit_id)

    def get_deposit_line_data(self, deposit_id: int, deposit_line_id: int) -> dict[str, Any]:
        return self.database.get_deposit_line_data(deposit_id, deposit_line_id)

    def authenticate_provider(self, username: str, password: int) -> dict[str, Any]:
        """"""
        with self.odoo.make_session() as session:
            auth, user = session.auth_provider(username, password)
            if auth is False:
                return {"auth": auth, "user": None}
            oid, code, name = session.user_to_record(user)
            end_shift_dist = session.get_current_shift_end_time_dist()
        db_user = self.database.get_user_from_code(code)
        if db_user is None:
            db_user = self.database.add_user(oid, code, name)

        user_id = db_user.get('user_id')
        self.database.update_activity(user_id, "provider")
        return {"auth": auth, "user": {"user_name": name, "user_code": code, "max_age":end_shift_dist}}
        
    def generate_ticket(self, deposit_id: int) -> None:
        """
        1. collect doposit & deposit_lines data
        2. build aggregated data for quantities and return values
        3. generate ticket
        4. return ticket in the printer accepted format
        """
        
        deposit = self.database.read_one("deposits", conditions=[("deposit_id", "=", deposit_id)])
        receiver_id = deposit.get("receiver_id")
        ean = deposit.get("deposit_barcode", None)

        receiver = self.database.read_one("users", fields=["user_code", "user_name"], conditions=[("user_id","=", receiver_id)])

        returns_per_types = self.database.get_returns_per_types(deposit_id)
        total_value = sum([r[2] for r in returns_per_types])

        if ean is None:
            ean = generate_ean(total_value)
            self.database.update("deposits", [("deposit_barcode", ean)], conditions=[("deposit_id", "=", deposit_id)])

        with self.printer.make_printer_session() as p:
            p.print_ticket(
                deposit_id=deposit_id,
                **receiver,
                returns_lines=returns_per_types,
                total_value=total_value,
                ean=ean
            )

    def search_user(self, value: str) -> list[tuple[int, str]]:
        """fuzzy search for the user."""
        with self.odoo.make_session() as session:
            res = session.fuzzy_user_search(value)
        return res

    def close_deposit(self, deposit_id: int) -> None:
        self.database.close_deposit(deposit_id)