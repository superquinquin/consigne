import re
import sys
from datetime import datetime
from sqlalchemy import Row, create_engine, select, insert, update, Result, text
from sqlalchemy.orm import sessionmaker, decl_api
from sqlalchemy import MetaData, Engine, Table
from sqlalchemy.sql.selectable import Select

from typing import Any, Optional, Literal, Callable, Type

"""
Schema is loaded dynamically using `ConsigneDatabase.load_metadata` method
As schemas are dynamic objects, for clarity we set: pyright: reportUndefinedVariable=false

"""

# pyright: reportUndefinedVariable=false


from src.schema import Base

class ConsigneDatabase:
    dialect: str
    database: str
    driver: Optional[str] | None
    host: Optional[str] | None
    port: Optional[int] | None
    username: Optional[str] | None
    password: Optional[str] | None
    
    _engine: Engine
    _metadata: MetaData

    def __init__(
        self, 
        dialect: str, 
        database: str,
        driver: Optional[str] | None = None,
        host: Optional[str] | None = None,
        port: Optional[int] | None = None,
        username: Optional[str] | None = None,
        password: Optional[str] | None = None
    ) -> None:
        self.dialect = dialect
        self.database = database
        self.driver = driver
        self.host = host
        self.port = port
        self.username = username
        self.password = password

        # self._prepare()
        self._engine = create_engine(self.uri)
        Base.metadata.create_all(self._engine, checkfirst=True)
        self._metadata = Base.metadata
        self.session_maker = sessionmaker(bind=self._engine)

        self.load_metadata(__name__)

    @property
    def uri(self) -> str:
        engine = f"{self.dialect}"
        if self.driver:
            engine += f"+{self.driver}"

        access = ""
        if all([self.username, self.password, self.host, self.port]):
            access = f"{self.username}:{self.password}@{self.host}:{str(self.port)}"
        return f"{engine}://{access}/{self.database}"



    def load_metadata(self, module_name: str) -> None:
        
        for k,v in self._metadata.tables.items():
            name = re.sub(r"[Mm]ain\.","", k)
            capitalized_name = name[0].upper() + name[1:]
            sys.modules[module_name].__dict__.update({capitalized_name:v})            


    def _collect_all_records(self, result: Result) -> list[dict[str, Any]]: 
        res = result.fetchall()
        return [r._asdict() for r in res]

    def _collect_one_record(self, result: Result) -> dict[str, Any] | None:
        res = result.fetchone()
        if res is not None:
            res = res._asdict()
        return res




    # USERS
    def add_user(self, partner_id: int, code: int, name: str) -> dict[str,Any] | None:
        with self.session_maker() as session:
            stmt = (
                insert(Users)
                .values(
                    user_partner_id=partner_id,
                    user_code=code,
                    user_name=name,
                    last_provider_activity=None,
                    last_receiver_activity=None
                )
                .returning(Users.c.user_id)
            )
            res = session.execute(stmt).fetchone()
            if res is not None:
                res = res._asdict()

            session.commit()
        return res

    def update_activity(self, user_id: int, activity_as: Literal["provider", "receiver"]) -> None:
        activity_field = f"last_{activity_as}_activity"
        field = getattr(Users, activity_field, None)
        if field is None:
            raise ValueError("Posible activity_as argument values are: [`provider`, `receiver`]")

        with self.session_maker() as session:
            stmt = (
                update(Users)
                .where(Users.c.user_id == user_id)
                .values({field:datetime.now().isoformat("-")})
            )
            session.execute(stmt)
            session.commit()

    def get_user_from_code(self, code: int) -> dict[str, Any] | None: 
        with self.session_maker() as session:
            stmt = (
                select(Users)
                .select_from(Users)
                .where(Users.c.user_code == code)
            )
            res = session.execute(stmt)
        return self._collect_one_record(res)

    def get_user_from_partner_id(self, partner_id: int) -> dict[str, Any] | None: 
        with self.session_maker() as session:
            stmt = (
                select(Users)
                .select_from(Users)
                .where(Users.c.user_partner_id == partner_id)
            )
            res = session.execute(stmt)
        return self._collect_one_record(res)

    def get_user_from_id(self, user_id: int) -> dict[str, Any]|None: 
        with self.session_maker() as session:
            stmt = (
                select(Users)
                .select_from(Users)
                .where(Users.c.user_id == user_id)
            )
            res = session.execute(stmt)
        return self._collect_one_record(res)

    # PRODUCTS
    def add_product(self, opid: int, name: str, barcode: str, return_product_id: int) -> dict[str, Any] | None:
        with self.session_maker() as session:
            stmt = (
                insert(Products)
                .values(
                    odoo_product_id=opid,
                    product_name=name,
                    barcode=barcode, 
                    product_return_id=return_product_id
                )
                .returning(Products.c.product_id))
            res = session.execute(stmt).fetchone()
            if res is not None:
                res = res._asdict()

            session.commit()
        return res

    def add_product_return(self, opid: int, name: str, returnable: bool, return_value: float) -> dict[str, Any] | None:
        with self.session_maker() as session:
            stmt = (
                insert(Product_returns)
                .values(
                    odoo_product_return_id=opid,
                    product_return_name=name,
                    returnable=returnable,
                    return_value=return_value
                )
                .returning(Product_returns.c.product_return_id)
            )
            res = session.execute(stmt).fetchone()
            if res is not None:
                res = res._asdict()

            session.commit()
        return res

    def update_deposit_barcode(self, deposit_id: int, ean: str, barcode_base_id: int) -> None:
        with self.session_maker() as session:
            stmt = (
                update(Deposits)
                .values(deposit_barcode=ean, 
                        deposit_barcode_base_id=barcode_base_id
                )
                .where(Deposits.c.deposit_id == deposit_id)
            )
            session.execute(stmt)
            session.commit()

    def update_deposit_redeem(self, deposit_id: int, redeem_id: int) -> None:
        with self.session_maker() as session:
            stmt = (
                update(Deposits)
                .values(Deposits.c.redeemed==redeem_id)
                .where(Deposits.c.deposit_id == deposit_id)
            )
            session.execute(stmt)
            session.commit()

    def get_product_from_opid(self, opid: int) -> dict[str, Any] | None: 
        with self.session_maker() as session:
            stmt = (
                select(Products)
                .where(Products.c.odoo_product_id == opid)
            )
            res = session.execute(stmt)
        return self._collect_one_record(res)

    def get_return_product_from_opid(self, opid: int) -> dict[str, Any] | None: 
        with self.session_maker() as session:
            stmt = (
                select(Product_returns)
                .where(Product_returns.c.odoo_product_return_id == opid)
            )
            res = session.execute(stmt)
        return self._collect_one_record(res)

    # DEPOSITS
    def add_deposit(self, receiver_id: int, provider_id: int) -> dict[str,Any] | None:
        with self.session_maker() as session:
            stmt = (
                insert(Deposits)
                .values(
                    receiver_id=receiver_id,
                    provider_id=provider_id,
                    deposit_datetime=datetime.now().isoformat("-"),
                    closed=False,
                    deposit_barcode=None,
                    redeemed=None
                )
                .returning(Deposits.c.deposit_id)
            )
            res = session.execute(stmt).fetchone()
            if res is not None:
                res = res._asdict()

            session.commit()
        return res


    def close_deposit(self, deposit_id: int) -> None:
        with self.session_maker() as session:
            stmt = (
                update(Deposits)
                .values(closed=True)
                .where(Deposits.c.deposit_id == deposit_id)
            )
            session.execute(stmt)
            session.commit()

    def add_deposit_line(self, deposit_id: int, product_id: int, canceled: bool=False) -> dict[str,Any] | None:
        with self.session_maker() as session:
            stmt = (
                insert(Deposit_lines)
                .values(
                    deposit_id=deposit_id,
                    product_id=product_id,
                    deposit_line_datetime=datetime.now().isoformat("-"),
                    canceled=canceled,
                )
                .returning(Deposit_lines.c.deposit_line_id)
            )
            res = session.execute(stmt).fetchone()
            if res is not None:
                res = res._asdict()

            session.commit()
        return res

    def cancel_returned_product(self, deposit_id: int, deposit_line_id:int) -> None:
        with self.session_maker() as session:
            stmt = (
                update(Deposit_lines)
                .values(canceled=True)
                .where(Deposit_lines.c.deposit_id == deposit_id)
                .where(Deposit_lines.c.deposit_line_id == deposit_line_id)
            )
            session.execute(stmt)
            session.commit()


    # GLOBAL
    def get_first_deposit_datetime(self) -> str | None:
        with self.session_maker() as session:
            stmt = (
                select(Deposits)
                .where(Deposits.c.deposit_id == 1)
            )

            res = session.execute(stmt)
            deposit = self._collect_one_record(res)
            if deposit is None:
                return
            return deposit.get("deposit_datetime")

    def get_last_redeem_datetime(self) -> str | None:
        with self.session_maker() as session:
            stmt = (
                select(Redeem)
                .order_by(Redeem.c.redeem_id.desc())
                .limit(1)
            )

            res = session.execute(stmt)
            redeem = self._collect_one_record(res)
            if redeem is None:
                return
            return redeem.get("redeem_datetime")

    def get_tracked_consigne_barcodes_bases(self) -> list[str]:
        with self.session_maker() as session:
            stmt = (
                select(Consigne.c.consigne_barcode_base)
                .select_from(Consigne)
            )

            res = session.execute(stmt)
            records = self._collect_all_records(res)
        bases = list(filter(None, [r.get("consigne_barcode_base") for r in records]))
        return bases

    def get_deposit_data(self, deposit_id: int) -> dict[str,Any]|None:
        with self.session_maker() as session:
            stmt = (
                select(Deposits)
                .where(Deposits.c.deposit_id == deposit_id)
            )


            res = session.execute(stmt)
            deposit = self._collect_one_record(res)
            if deposit is None:
                return deposit
            
            receiver_id = deposit.get("receiver_id")
            provider_id = deposit.get("provider_id")

            reciever_stmt = (
                Select(Users)
                .where(Users.c.user_id == receiver_id)
            )
            provider_stmt = (
                Select(Users)
                .where(Users.c.user_id == provider_id)
            )

            receiver = self._collect_one_record(session.execute(reciever_stmt))
            provider = self._collect_one_record(session.execute(provider_stmt))

            stmt = (    
                select(Deposit_lines, Products, Product_returns)
                .select_from(Deposit_lines)
                .join(Products)
                .join(Product_returns)
                .where(Deposit_lines.c.deposit_id == deposit_id)
            )

            res = session.execute(stmt)
            deposit_lines = self._collect_all_records(res)
        return {
            "deposit": deposit,
            "provider": provider,
            "receiver": receiver,
            "deposit_lines": deposit_lines
        }


    def get_deposit_line_data(self, deposit_id: int, deposit_line_id: int) -> dict[str, Any] | None:
        with self.session_maker() as session:
            stmt = (
                select(Deposit_lines)
                .join(Products)
                .join(Product_returns)
                .where(Deposit_lines.c.deposit_id == deposit_id)
                .where(Deposit_lines.c.deposit_line_id == deposit_line_id)
            )
            res = session.execute(stmt)
        return self._collect_one_record(res)

    def get_returns_per_types(self, deposit_id) -> list[Row]:
        RETURNS_PER_PRODUCT_TYPE = """\
            SELECT 
                product_returns.product_return_name, 
                COUNT(deposit_line_id), 
                ROUND(CAST(SUM(product_returns.return_value) AS NUMERIC), 2)
            FROM main.deposit_lines 
            JOIN main.products ON main.deposit_lines.product_id=main.products.product_id 
            JOIN main.product_returns ON main.products.product_return_id=main.product_returns.product_return_id 
            WHERE 
                deposit_id = :did
                AND canceled = False 
                AND main.product_returns.product_return_id != 1
            GROUP BY products.product_return_id, product_returns.product_return_name;
            """

        with self.session_maker() as session:
            res = session.execute(text(RETURNS_PER_PRODUCT_TYPE), {'did':deposit_id}).fetchall()
        return list(res)

    # REDEEM
    def match_redeem_deposits(self, barcode: str, partner_id: int, value: float) -> list[dict[str, Any]]: 
        POS_REDEEM_MATCHING = """\
            SELECT 
                deposits.deposit_id
            FROM main.deposits
            JOIN main.deposit_lines ON main.deposit_lines.deposit_id=main.deposits.deposit_id
            JOIN main.users ON main.users.user_id=deposits.receiver_id
            JOIN main.products ON main.deposit_lines.product_id=main.products.product_id 
            JOIN main.product_returns ON main.products.product_return_id=main.product_returns.product_return_id 
            WHERE
                deposits.deposit_barcode = :barcode
                AND user_partner_id = :pid
                AND deposits.redeemed IS NULL
                AND deposits.closed = True
            GROUP BY deposits.deposit_id
            HAVING ROUND(CAST(SUM(product_returns.return_value) AS NUMERIC), 2) = :value
            ORDER BY deposit_id;
            """
        with self.session_maker() as session:
            res = session.execute(text(POS_REDEEM_MATCHING), {'pid':partner_id, "barcode": barcode, "value": value})
            res = self._collect_all_records(res)
        return res

    def add_redeem(self, order_id: int, dt: str, user_id: int, value: float, barcode: str, anomaly: bool) -> dict[str, Any] | None:
        with self.session_maker() as session:
            stmt = (
                insert(Redeem)
                .values(
                    odoo_pos_id=order_id,
                    redeem_datetime=dt,
                    redeem_user=user_id,
                    redeem_value=value,
                    redeem_barcode=barcode,
                    anomaly=anomaly,
                )
                .returning(Redeem.c.redeem_id)                
            )
            res = session.execute(stmt).fetchone()
            if res is not None:
                res = res._asdict()

            session.commit()
        return res
    
    def _update_consigne_barcodes(self, records: tuple) -> None:
        with self.session_maker() as session:
            stmt = (
                select(Consigne.c.consigne_barcode_base)
            )

            bases = [r[0] for r in session.execute(stmt).fetchall()]
            for base, barcode, name, sale_ok in records:
                if base not in bases and sale_ok:
                    stmt = (
                        insert(Consigne)
                        .values(
                            consigne_name=name,
                            consigne_barcode=barcode,
                            consigne_barcode_base=base,
                            consigne_active=True
                        )
                    )
                    session.execute(stmt)
                elif base in bases and sale_ok is False:
                    stmt = (
                        update(Consigne)
                        .values(consigne_active=False)
                        .where(Consigne.c.consigne_barcode_base == base)
                    )
                    session.execute(stmt)
            session.commit()

    def next_barcode_base(self) -> tuple[int, int | None]:
        with self.session_maker() as session:
            stmt = (
                select(Deposits.c.deposit_barcode_base_id)
                .where(Deposits.c.deposit_barcode_base_id != None)
                .order_by(Deposits.c.deposit_id.desc())
                .limit(1)
            )
            res = session.execute(stmt).fetchone() or (0,)
            consigne_id = res[0]

            base = None
            base_id = consigne_id + 1
            while base is None:
                base = self._get_base(base_id)
                if base is None and base_id == 1:
                    raise ValueError("No consigne barcode found")
                elif base is None:
                    base_id = 1
        return (base_id, base)
        

    def _get_base(self, consigne_id: int) -> int | None:
        with self.session_maker() as session:
            stmt = (
                select(Consigne.c.consigne_barcode_base)
                .select_from(Consigne)
                .where(Consigne.c.consigne_id == consigne_id)
            )

        res = session.execute(stmt).fetchone()
        if res is not None:
            return res[0]
        return