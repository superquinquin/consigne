from __future__ import annotations

import os
import time
from contextlib import ContextDecorator
from datetime import datetime
from functools import wraps, lru_cache
from http.client import CannotSendRequest
from erppeek import Client, Record, RecordList

from typing import Callable, Any

Conditions = list[tuple[str, str, Any]]

FZ_LIMIT = 5
SHIFT_DT_TOLERANCE = 5

def resilient(degree: int = 3):
    def decorator(f: Callable):
        @wraps(f)
        def wrapper(*args, **kwargs):
            self: OdooSession = args[0]
            success, tries = False, 0
            while success is False and tries <= degree:
                try:
                    res = f(*args, **kwargs)
                    success = True
                except (CannotSendRequest, AssertionError):
                    tries += 1
                    self.renew_session()
            return res
        return wrapper
    return decorator


class OdooConnector(object):
    """Odoo connection handler & session factory"""
    host: str
    database: str
    verbose: bool

    def __init__(self, host: str, database: str, verbose: bool = False, **kwargs):
        self.host = host
        self.database = database
        self.verbose = verbose

    def make_session(self, max_retries: int = 5, retries_interval: int = 5):
        username = os.environ.get("ERP_USERNAME", None)
        password = os.environ.get("ERP_PASSWORD", None)
        if not all([username, password]):
            raise ValueError("ERP_USERNAME and/or ERP_PASSWORD ENV variables not found")
        
        success, tries = False, 0
        while (success is False and tries <= max_retries):
            try:
                client = Client(self.host, verbose=self.verbose)
                client.login(username, password=password, database=self.database)
                success = True
            except Exception:
                time.sleep(retries_interval)
                tries += 1

        if success is False:
            raise ConnectionError("Unable to generate an Odoo Session")
        return OdooSession(client)

class OdooSession(ContextDecorator):
    client: Client

    def __init__(self, client: Client):
        self.client = client

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, exc_tb):
        del self

    @resilient(degree=3)
    def get(self, model: str, conditions: Conditions) -> Record:
        return self.client.model(model).get(conditions)

    @resilient(degree=3)
    def browse(self, model: str, conditions: Conditions) -> RecordList:
        return self.client.model(model).browse(conditions)

    def renew_session(self) -> None:
        username = os.environ.get("ERP_USERNAME", None)
        password = os.environ.get("ERP_PASSWORD", None)
        if not all([username, password]):
            raise ValueError("ERP_USERNAME or ERP_PASSWORD env variables not found")
        client = Client(self.client._server, verbose=False)
        client.login(username, password=password, database=self.client._db)
        self.client = client

    def get_product_from_barcode(self, barcode: str) -> Record:
        return self.get("product.product", [("barcode", "=", barcode)])

    def get_product_return(self, product: Record) -> tuple[bool, Record|None]:
        """
        takes a product.product record as argument.
        return a tuple describing both 
        returnability of the product (bool) 
        and the it's associated return_product (Record of product.product)
        """
        tmpl = product.product_tmpl_id
        return (tmpl.returnable, tmpl.return_product_id or None)

    def product_to_record(self, product: Record) -> tuple:
        tmpl = product.product_tmpl_id
        return (product.id, tmpl.name, product.barcode)

    def product_return_to_record(self, product_return: Record) -> tuple:
        tmpl = product_return.product_tmpl_id
        return (product_return.id, tmpl.name, True, tmpl.list_price)

    def auth_provider(self, username: str, password: str) -> tuple[bool, Record|None]:
        c = Client(self.client._server, verbose=False)
        auth = c._auth(self.client._db, username, password)
        if auth[0] is False:
            return (False, None)
        user = self.get("res.users", [("id", "=", auth[0])])
        return (True, user)

    def user_to_record(self, user: Record) -> tuple:
        partner = user.partner_id
        return (partner.id, partner.barcode_base, partner.name)
    
    def get_partner_record_from_code(self, code: int) -> tuple:
        partner = self.get("res.partner", [("barcode_base", "=", code)])
        return (partner.id, partner.barcode_base, partner.name)
    
    def fuzzy_user_search(self, value: str) -> list[tuple[int, str]]:
        """return list of users close from the given value. 
        infer method given value type. resulting list size depend on FZ_LIMIT"""
        if value.isnumeric():
            res = self.fuzzy_code_search(value)
        else:
            res = self.fuzzy_name_search(value)
        return res

    @lru_cache(maxsize=32)
    def fuzzy_code_search(self, user_code: int) -> list[tuple[int, str]]:
        res = self.browse("res.partner", [("barcode_base", "like", user_code)])
        print("code", res)
        return [(r.barcode_base, r.display_name) for r in res[:FZ_LIMIT]]

    @lru_cache(maxsize=32)
    def fuzzy_name_search(self, name: int) -> list[tuple[int, str]]:
        res = self.browse("res.partner", [("name", "ilike", name)])
        print("name", res)
        return [(r.barcode_base, r.display_name) for r in res[:FZ_LIMIT]]

    def get_current_shift_end_time_dist(self) -> int|None:
        """return dist from current shift end time in seconds"""
        dt_day = datetime.now().replace(hour=0)
        shifts = self.browse("shift.shift", [("date_begin_tz", ">", dt_day), ("date_begin_tz", "<", datetime.now())])
        if len(shifts) == 0:
            return None
        current = shifts[-1]
        dist = int((datetime.fromisoformat(current.date_end_tz) - datetime.now()).total_seconds())
        if dist < 0:
            dist = None
        return dist

    