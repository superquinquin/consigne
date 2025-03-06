from __future__ import annotations

import os
import time
from datetime import datetime
from functools import wraps
from http.client import CannotSendRequest
from erppeek import Client, Record, RecordList

from typing import Callable, Any

Conditions = list[tuple[str, str, Any]]

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




class OdooSession(object):
    client: Client

    def __init__(self, client: Client):
        self.client = client

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
        

    def is_product_deposable(self, product: Record) -> bool:
        ...

    def get_product_deposit_value(self, product: Record) -> float:
        ...

    def get_current_shift_end_time(self) -> datetime:
        ...

    def provider_auth(self, username: str, password: str) -> bool:
        ...