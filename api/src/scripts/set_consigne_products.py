from __future__ import annotations

import re
import random
from pathlib import Path
from erppeek import Client, Record
from dataclasses import dataclass, field, asdict
from collections import deque
from functools import reduce

from sqlalchemy import insert

from typing import Any, Generator


from src.loaders import ConfigLoader
from src.odoo import OdooSession
from src.database import ConsigneDatabase

PARENT_CAT = "Consigne"
RETURN_CAT = "Consigne_return"
PRODUCT_CAT = "Consigne_product"

# pyright: reportUndefinedVariable=false

@dataclass(frozen=True)
class Product:
    name: str = field()
    categ_id: int = field()
    barcode: str|None = field(default=None)
    barcode_base: str|None = field(default=None)
    barcode_pattern: str|None = field(default=None)
    returnable: bool = field(default=False)
    return_product_id: int| None = field(default=None)
    uom_id: int = field(default=1)
    sale_ok: bool = field(default=True)
    purchase_ok: bool = field(default=False)
    value: float|None = field(default=None)
    available_in_pos: bool|None = field(default=False)
    fiscal_classification_id: int|None = field(default=None) 

    def as_payload(self) -> dict[str, Any]:
        return {k:v for k,v in asdict(self).items() if v is not None}

    def return_payload(self):
        payload = self.as_payload()
        payload["sale_ok"] = False
        payload["list_price"] = payload.pop("value")
        payload["fiscal_classification_id"] = 3 # no taxes
        return payload

    def product_payload(self):
        payload = self.as_payload()
        payload["fiscal_classification_id"] = 3 # no taxes
        payload["available_in_pos"] = True
        payload.pop("barcode_pattern")
        return payload

class BuildingDatabase(ConsigneDatabase):
    def __init__(self, dialect, database, driver = None, host = None, port = None, username = None, password = None):
        super().__init__(dialect, database, driver, host, port, username, password)
        self.load_metadata(__name__)

    def add_consigne_product(self, product: Product):
        with self.session_maker() as session:
            stmt = (
                insert(Consigne)
                .values(
                    consigne_pattern=product.barcode_pattern,
                    consigne_name=product.name,
                    consigne_barcode=product.barcode,
                    consigne_barcode_base=product.barcode_base,
                    consigne_active=True
                )
            )
            session.execute(stmt)
            session.commit()

class BuildingOdoo(OdooSession):
    def __init__(self, client):
        super().__init__(client)

    def create_consigne_cat(self) -> tuple[Record, Record, Record]: 
        parent_cat = self.get("product.category", [("name","=", PARENT_CAT)])
        product_cat = self.get("product.category", [("name","=", PRODUCT_CAT)])
        return_cat = self.get("product.category", [("name","=", RETURN_CAT)])

        if parent_cat is None:
            parent_cat = self.client.model("product.category").create({
                "parent_id": None,
                "name": "Consigne",
                "type": "normal"
            })

        if product_cat is None:
            product_cat = self.client.model("product.category").create({
                "parent_id": parent_cat.id,
                "name": "Consigne_product",
                "type": "normal"
            })

        if return_cat is None:
            return_cat = self.client.model("product.category").create({
                "parent_id": parent_cat.id,
                "name": "Consigne_return",
                "type": "normal"
            })
        return (parent_cat, product_cat, return_cat)

    def create_consigne_product(self, product: Product) -> None:
        p = self.get("product.product", [("barcode","=", product.barcode)])

        if p is None:
            print("CREATING PRODUCT")
            r = self.client.model("product.product").create({"name": product.name})
            tmpl = r.product_tmpl_id
            for k,v in product.product_payload().items():
                setattr(tmpl, k, v)

    def create_consigne_product_returns(self, product: Product) -> None:
        p = self.get("product.product", [("name","=", product.name)]) # incentive to make name unique 
        
        if p is None:
            print("CREATING RETURNS")
            r = self.client.model("product.product").create({"name": product.name})
            tmpl = r.product_tmpl_id
            for k,v in product.return_payload().items():
                setattr(tmpl, k, v)
    

    def set_to_returnable(self, barcode: str, returnable:bool, returned: str) -> None:
        returns = self.get("product.product", [("name","=", returned)])
        p = self.get("product.product", [("barcode","=", str(barcode))])

        if not all([returns, p]):
            print(f">>> Failed to update product: {(barcode, returnable, returned)}")
            return

        if returnable is True:        
            p.product_tmpl_id.returnable = True
            p.product_tmpl_id.return_product_id = returns.id
        else:
            p.product_tmpl_id.returnable = False

    def get_existing_consigne_barcodes(self, product_cat_id:int) -> list[tuple]:
        return [(r.barcode_base, r.barcode) for r in self.browse("product.product", [("product_tmpl_id.categ_id.id", "=", product_cat_id)])]


class BarcodeGenerator(object):
    def __init__(self, rule: str, avoid: list[tuple], number: int=1, in_place: bool = True):
        self.rule = rule
        self.avoid = avoid
        self.variation_number = number
        if in_place:
            self.variation_number =  number - len(avoid)
            if self.variation_number <= 0:
                self.variation_number = 0
            
    def generate_barcode(self) -> Generator[tuple[str, str]]:
        for _ in range(self.variation_number):
            uniq = False
            while uniq is False:
                base_values = [str(random.randrange(10)) for _ in re.findall(r"\.", self.rule)]
                if len(self.avoid) == 0:
                    uniq = True
                elif not any(["".join(base_values) == str(base) for base, _ in self.avoid]):
                    uniq = True
            barcode_base = "".join(base_values)
            self.avoid.append((barcode_base, ""))

            filler_values = [str(random.randrange(10)) for _ in re.findall(r"N|D", self.rule)]

            barcode = self._barcode(deque(base_values), deque(filler_values))
            yield (barcode_base, barcode + str(self._checksum(barcode)))

    def _barcode(self, base: deque, filler: deque):
        barcode = ""
        for v in self.rule:
            if bool(re.search(r"[0-9]", v)):
                barcode += v
            elif bool(re.search(r"\.", v)):
                barcode += str(base.popleft())
            elif bool(re.search(r"N|D", v)):
                barcode += str(filler.popleft())
            else:
                continue
        return barcode
    
    @staticmethod
    def _checksum(ean: str) -> int:
        sum = lambda x, y: int(x) + int(y)
        evensum = reduce(sum, ean[::2])
        oddsum = reduce(sum, ean[1::2])
        return (10 - ((evensum + oddsum * 3) % 10)) % 10
    


class Builder(object):
    odoo: BuildingOdoo
    database: BuildingDatabase

    returns: list[dict[str, Any]]
    products: dict[str, Any]
    returnables: list[dict[str, Any]]

    
    def __init__(
        self, 
        odoo: BuildingOdoo, 
        database: BuildingDatabase, 
        returns: list[dict[str, Any]],
        products: dict[str, Any],
        returnables: list[dict[str, Any]]
    ):
        self.odoo = odoo
        self.database = database

        self.returns = returns
        self.products = products
        self.returnables = returnables

    @classmethod
    def from_configs(cls, path: str|Path) -> Builder:
        configs = ConfigLoader().load(path)
        
        odoo_cfg = configs.get("odoo", None)
        database_cfg = configs.get("database", None)

        if not all([odoo_cfg, database_cfg]):
            raise ValueError("Provide configuration for Odoo and the database.")
        
        erp_cfg = odoo_cfg.get("erp", None)
        taxonomy = odoo_cfg.get("taxonomy", {})
        
        if not erp_cfg:
            raise ValueError("Provide ERP configurations")

        products = taxonomy.get("products", [])
        returns = taxonomy.get("returns", [])
        returnables = taxonomy.get("returnables", [])
        
        
        odoo = BuildingOdoo(cls._make_client(**erp_cfg))
        database = BuildingDatabase(**database_cfg)
        return cls(odoo, database, returns, products, returnables)

    def run(self):
        parent_cat, product_cat, return_cat = self.odoo.create_consigne_cat()
        
        self.set_returns(return_cat.id)
        self.set_products(product_cat.id)
        self.set_returnables()
        
    def set_products(self, categ_id: int) -> None:
        current_barcodes = self.odoo.get_existing_consigne_barcodes(categ_id)

        in_place = self.products.get("in_place", True)
        variation = self.products.get("variation_number", 1)
        template = self.products.get("template", None)
        if template is None:
            raise KeyError("You must define a consigne product template")
        rule = template.get("rule", None)
        name = template.get("name", "Consigne")
        if rule is None:
            raise KeyError("You must define a consigne product barcode rule")
    
        generator = BarcodeGenerator(rule, current_barcodes, variation, in_place)
        for base, barcode in generator.generate_barcode():
            product = Product(name, categ_id, barcode, base, rule)
            self.odoo.create_consigne_product(product)  
            try:
                self.database.add_consigne_product(product)
            except Exception:
                print("conflict happen")

    def set_returns(self, categ_id: int) -> None:
        returns = self._make_returns_products(categ_id)
        for ret in returns:
            self.odoo.create_consigne_product_returns(ret)

    def set_returnables(self) -> None:
        for ret in self.returnables:
            self.odoo.set_to_returnable(**ret)

    def _make_returns_products(self, categ_id: int) -> list[Product]:
        return [Product(**x, categ_id=categ_id) for x in self.returns]

    @staticmethod
    def _make_client(host: str, database: str, login: str, password: str,  verbose: bool=False) -> Client:
        client = Client(host, verbose=verbose)
        client.login(login, password=password, database=database)
        return client