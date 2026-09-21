from __future__ import annotations

import os
import time
from contextlib import ContextDecorator
from datetime import datetime, timedelta
from functools import wraps, lru_cache
from http.client import CannotSendRequest
from urllib.parse import urlsplit, urlunsplit, quote
from odooly import Client, Record, RecordList, Model

from typing import Callable, Any

# pyright: reportAttributeAccessIssue=false
# pyright: reportFunctionMemberAccess=false

Conditions = list[tuple[str, str, Any]]


def _jsonable(value: Any) -> Any:
    """Make a domain value safe for Odooly's JSON-RPC transport.

    ErpPeek spoke XML-RPC, which marshalled ``datetime`` natively. Odooly
    serialises the domain with ``json.dumps``, which raises TypeError on a
    ``datetime`` -- so datetimes are converted to the ISO strings Odoo
    expects. Applied at the session seam rather than at each call site, so
    callers may keep passing datetimes.
    """
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (list, tuple)):
        return type(value)(_jsonable(v) for v in value)
    return value


def normalize_conditions(conditions: Conditions) -> Conditions:
    return [_jsonable(clause) for clause in conditions]


def field(record: Record, name: str) -> Any:
    """Read a field, refusing Odooly's silent method fallback.

    ``Record.__getattr__`` never raises for an unknown field: anything not in
    ``_model._keys`` is assumed to name an Odoo model *method* and comes back
    as a bound callable. So a field renamed between Odoo versions -- or one
    whose addon is not installed -- yields a method object instead of an
    error, and that object flows on into the ledger and into the EAN13 that
    encodes the refund amount. Reading through this helper turns that silent
    corruption into an immediate AttributeError.
    """
    if name not in record._model._keys:
        raise AttributeError(
            f"model {record._model._name!r} has no field {name!r} on this Odoo "
            f"instance (Odooly would have returned a bound method here)"
        )
    return getattr(record, name)


Zone = tuple[datetime | None, datetime | None]


FZ_LIMIT = 10
SHIFT_DT_TOLERANCE = 5
SHIFT_LEN = timedelta(hours=2, minutes=45)

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
                    return res
                except (CannotSendRequest, AssertionError):
                    tries += 1
                    self.renew_session()
            raise ConnectionError("Cannot establish connection with odoo.")
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

    @property
    def url(self) -> str:
        """Server URL, carrying HTTP Basic credentials as userinfo when the
        instance sits behind a protected reverse proxy (Trobz staging).

        Odooly reads the credentials straight off the URL; they must be
        re-injected on every Client construction, because Odooly strips the
        userinfo from ``client._server`` once connected.
        """
        user = os.environ.get("ERP_BASIC_USER", None)
        password = os.environ.get("ERP_BASIC_PASSWORD", None)
        if not all([user, password]):
            return self.host
        split = urlsplit(self.host)
        host = split.netloc.rsplit("@", 1)[-1]
        userinfo = f"{quote(str(user), safe='')}:{quote(str(password), safe='')}"
        return urlunsplit((split.scheme, f"{userinfo}@{host}", split.path, split.query, split.fragment))

    @staticmethod
    def credentials() -> tuple[str, str | None, str | None]:
        """(user, password, api_key).

        Odoo 14+ supports API keys, and deployments commonly disable password
        authentication for external RPC while keeping it for the web UI --
        which fails with "Invalid username or password" on credentials that
        are perfectly valid. Setting ERP_API_KEY switches to key auth.
        """
        username = os.environ.get("ERP_USERNAME", None)
        api_key = os.environ.get("ERP_API_KEY", None)
        password = os.environ.get("ERP_PASSWORD", None)
        if username is None or not any([password, api_key]):
            raise ValueError(
                "ERP_USERNAME and one of ERP_PASSWORD / ERP_API_KEY must be set"
            )
        return (username, api_key or password, api_key)

    def make_session(self, max_retries: int = 5, retries_interval: int = 5) -> OdooSession:
        username, password, api_key = self.credentials()
        
        success, tries, last_error = False, 0, None
        while (success is False and tries <= max_retries):
            try:
                client = Client(
                    self.url, self.database, username, password,
                    api_key=api_key, verbose=self.verbose,
                )
                success = True
                return OdooSession(client, self)
            except Exception as exc:
                last_error = exc
                time.sleep(retries_interval)
                tries += 1
        # Surface the cause: a rejected password and an unreachable host are
        # otherwise indistinguishable after five silent retries.
        raise ConnectionError(
            f"Unable to generate an Odoo Session: {type(last_error).__name__}: {last_error}"
        ) from last_error
        

class OdooSession(ContextDecorator):
    client: Client
    connector: "OdooConnector"

    def __init__(self, client: Client, connector: "OdooConnector"):
        self.client = client
        self.connector = connector

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, exc_tb):
        del self

    @resilient(degree=3)
    def get(self, model: str, conditions: Conditions) -> Record | None:
        return self.client.env[model].get(normalize_conditions(conditions))

    @resilient(degree=3)
    def search(self, model: str, conditions: Conditions) -> RecordList:
        """Records matching a domain.

        Odooly's ``Model.browse()`` only accepts ids -- handing it a domain
        raises AssertionError -- so a domain lookup goes through ``search()``,
        which returns a RecordList.
        """
        return self.client.env[model].search(normalize_conditions(conditions))

    def renew_session(self) -> None:
        username, password, api_key = self.connector.credentials()
        client = Client(
            self.connector.url, self.client.env.db_name, username, password,
            api_key=api_key, verbose=False,
        )
        self.client = client

    def get_product_from_barcode(self, barcode: str) -> Record | None:
        return self.get("product.product", [("barcode", "=", barcode)])

    def get_product_return(self, product: Record) -> tuple[bool, Record | None]:
        """
        takes a product.product record as argument.
        return a tuple describing both 
        returnability of the product (bool) 
        and the it's associated return_product (Record of product.product)
        """
        tmpl = field(product, "product_tmpl_id")
        return (field(tmpl, "returnable"), field(tmpl, "return_product_id") or None)

    def product_to_record(self, product: Record) -> tuple:
        tmpl = field(product, "product_tmpl_id")
        return (product.id, field(tmpl, "name"), field(product, "barcode"))

    def product_return_to_record(self, product_return: Record) -> tuple:
        tmpl = field(product_return, "product_tmpl_id")
        return (product_return.id, field(tmpl, "name"), True, field(tmpl, "list_price"))

    def auth_provider(self, username: str, password: str) -> tuple[bool, Record|None]:
        """Validate an operator's credentials on a throwaway client.

        Odooly exposes no non-mutating credential check here: ``client.common``
        is None whenever the server URL has no ``/jsonrpc`` path, and
        ``Client.login()`` swaps ``self.env`` in place -- so authenticating on
        the service client would re-bind this session to the operator.
        """
        try:
            c = Client(
                self.connector.url, self.client.env.db_name, username, password, verbose=False
            )
        except Exception:
            return (False, None)
        if not c.env.uid:
            return (False, None)
        user = self.get("res.users", [("id", "=", c.env.uid)])
        return (True, user)

    def user_to_record(self, user: Record) -> tuple:
        partner = field(user, "partner_id")
        return (partner.id, field(partner, "barcode_base"), field(partner, "name"))
    
    def get_partner_record_from_code(self, code: int) -> list[tuple]:
        partners = self.search("res.partner", [("barcode_base", "=", code), ("cooperative_state", "!=", "unsubscribed")])
        return [(partner.id, partner.barcode_base, partner.name) for partner in partners]
    
    def get_partner_record_from_id(self, partner_id: int) -> tuple | None:
        partner = self.get("res.partner", [("id", "=", partner_id), ("cooperative_state", "!=", "unsubscribed")])
        if partner is None:
            return
        return (partner.id, partner.barcode_base, partner.name)

    def fuzzy_user_search(self, value: str) -> list[tuple[int, int, str]]:
        """return list of users close from the given value. 
        infer method given value type. resulting list size depend on FZ_LIMIT"""
        if value.isnumeric():
            res = self.fuzzy_code_search(int(value))
        else:
            res = self.fuzzy_name_search(value)
        return res

    # @lru_cache(maxsize=32)
    def fuzzy_code_search(self, user_code: int) -> list[tuple[int, int, str]]:
        """have to be a browse because barcode_base is not unique, but op can be ="""
        if user_code < 0:
            raise ValueError("Negative value barcode_base are not allowed")
        if user_code > 65535:
            raise ValueError("user barcode_base larger than u16")

        res = self.search("res.partner", [("barcode_base", "=", user_code), ("cooperative_state", "!=", "unsubscribed")])
        return [(r.id, r.barcode_base, r.display_name) for r in res]

    # @lru_cache(maxsize=32)
    def fuzzy_name_search(self, name: str) -> list[tuple[int, int, str]]:
        res = self.search("res.partner", [("name", "ilike", name), ("cooperative_state", "!=", "unsubscribed")])
        return [(r.id, r.barcode_base, r.display_name) for r in res[:FZ_LIMIT]]

    def get_current_shift_end_time_dist(self) -> int|None:
        """return dist from current shift end time in seconds"""
        dt_day = datetime.now().replace(hour=0)
        shifts = self.search("shift.shift", [("date_begin_tz", ">", dt_day), ("date_begin_tz", "<", datetime.now())])
        if len(shifts) == 0:
            return None
        current = shifts[-1]
        dist = int((datetime.fromisoformat(current.date_end_tz) - datetime.now()).total_seconds())
        if dist < 0:
            dist = None
        return dist

    def get_redeemed_tickets(self, bases: list[str], before: datetime, after: datetime) -> list[Record]:
        """research specific barcodes in pos.order_lines before and after certain dates. return matched records"""
        return self.search("pos.order.line", [("product_id.barcode_base", "in", bases), ("create_date", ">=", after), ("create_date", "<", before)])
        
    def pos_order_line_to_record(self, record: Record) -> tuple:
        return (
            field(record, "order_id").id,
            field(record, "create_date"),
            field(record, "price_unit"),
            field(field(record, "product_id"), "barcode"),
        )
    
    def get_existing_consigne_barcodes(self) -> list[tuple]:
        product_cat = self.get("product.category", [("name", "=", "Consigne_product")])
        if product_cat is None:
            raise ValueError("Setup Odoo consigne taxonomies first.")
        product_cat_id = product_cat.id
        return [(str(r.barcode_base), r.barcode, r.name, r.sale_ok) for r in self.search("product.product", [("product_tmpl_id.categ_id.id", "=", product_cat_id)])]

    def get_current_shifts(self) -> RecordList:
        SHIFT_WINDOW_FLOOR = int(os.environ.get("SHIFT_WINDOW_FLOOR", 15))
        SHIFT_WINDOW_CEILING = int(os.environ.get("SHIFT_WINDOW_CEILING", 15))

        begin = (datetime.now() - SHIFT_LEN - timedelta(minutes=SHIFT_WINDOW_FLOOR)).isoformat()
        end = (datetime.now() + timedelta(minutes=SHIFT_WINDOW_CEILING)).isoformat()
        shifts = self.search("shift.shift", [("date_begin_tz", ">=", begin), ("date_begin_tz", "<=", end), ("shift_type_id.id", "=", 1)])
        return shifts

    def get_shift_zone(self, shifts: RecordList) -> tuple[datetime | None, datetime | None]:
        SHIFT_WINDOW_FLOOR = int(os.environ.get("SHIFT_WINDOW_FLOOR", 15))
        SHIFT_WINDOW_CEILING = int(os.environ.get("SHIFT_WINDOW_CEILING", 15) )
        debut, end = None, None

        if len(shifts) == 1:
            shift = shifts[0]
            dt_begin = shift.date_begin_tz
            dt_end = shift.date_end_tz
            assert isinstance(dt_begin, str) and isinstance(dt_end, str)
            debut = datetime.fromisoformat(dt_begin) + timedelta(minutes=SHIFT_WINDOW_FLOOR)
            end = datetime.fromisoformat(dt_end) - timedelta(minutes=SHIFT_WINDOW_CEILING) 

        elif len(shifts) == 2:
            first_shift, second_shift = shifts[0], shifts[1]
            dt_begin = second_shift.date_begin_tz
            dt_end = first_shift.date_end_tz
            assert isinstance(dt_begin, str) and isinstance(dt_end, str)
            debut = datetime.fromisoformat(dt_begin) - timedelta(minutes=SHIFT_WINDOW_FLOOR)
            end = datetime.fromisoformat(dt_end) + timedelta(minutes=SHIFT_WINDOW_CEILING) 

        return (debut, end)

    def get_shifts_members(self, shifts: RecordList) -> list[tuple[int, int, str]]:
        current_members = []
        for shift in shifts:
            members = self.search("shift.registration", [("shift_id", "=", shift.id)])
            current_members.extend([(r.partner_id.id, r.partner_id.barcode_base, r.partner_id.display_name) for r in members])

        current_members = sorted(current_members, key= lambda x: x[1])
        return current_members
    
    def get_current_shifts_members(self) -> tuple[Zone, list[tuple[int, int, str]]]:
        shifts = self.get_current_shifts()
        zone = self.get_shift_zone(shifts)
        if len(shifts) == 0:
            members = []
        else:
            members = self.get_shifts_members(shifts)
        return (zone, members)