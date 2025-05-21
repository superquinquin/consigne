import sys
from datetime import datetime
from sqlalchemy import Row, create_engine, select, insert, update, Result, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy import MetaData, Engine, Table
from sqlalchemy.sql.selectable import Select

from typing import Any, Optional, Literal, Callable

"""
Schema is loaded dynamically using `ConsigneDatabase.load_metadata` method
As schemas are dynamic objects, for clarity we set: pyright: reportUndefinedVariable=false

"""

# pyright: reportUndefinedVariable=false

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

        self._engine = create_engine(self.uri)
        self._metadata = MetaData()
        self._metadata.reflect(self._engine)
        self.session_maker = sessionmaker(bind=self._engine)

        self.load_metadata(__name__)

    @property
    def uri(self) -> str:
        engine = f"{self.dialect}"
        if self.driver:
            engine += f"+{self.driver}"

        access = ""
        if all([self.username, self.password, self.host, self.port]):
            access = f"{self.username}:{self.password}@{self.host}:{int(self.port)}"
        return f"{engine}://{access}/{self.database}"

    def load_metadata(self, module_name: str) -> None:
        for k, v in self._metadata.tables.items():
            k_up = k[0].upper() + k[1:]
            table = Table(k, self._metadata)
            [setattr(table, cname, c) for cname,c in table.columns.items()]    
            sys.modules[module_name].__dict__.update({k_up:table})            

    def _collect(self, result: Result, fetch: Literal["one", "all"], as_dict: bool=True, serialize: bool=True) -> dict[str, Any]|None:
        collect: Callable = getattr(Result, f"fetch{fetch}")
        res = collect(result)
        if res is None:
            return None
        if as_dict and fetch == "all":
            return [r._asdict() for r in res]
        if as_dict:
            return res._asdict()
        return res
    
    # USERS
    def add_user(self, partner_id: int, code: int, name: str) -> dict[str,Any]:
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
                .returning(Users.user_id)
            )
            res = session.execute(stmt).fetchone()._asdict()
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
                .where(Users.user_id == user_id)
                .values({field:datetime.now().isoformat("-")})
            )
            session.execute(stmt)
            session.commit()

    def get_user_from_code(self, code: int) -> dict[str, Any]|None: 
        with self.session_maker() as session:
            stmt = (
                select(Users)
                .select_from(Users)
                .where(Users.user_code == code)
            )
            res = session.execute(stmt)
        return self._collect(res, "one")

    def get_user_from_id(self, user_id: int) -> dict[str, Any]|None: 
        with self.session_maker() as session:
            stmt = (
                select(Users)
                .select_from(Users)
                .where(Users.user_id == user_id)
            )
            res = session.execute(stmt)
        return self._collect(res, "one")

    # PRODUCTS
    def add_product(self, opid: int, name: str, barcode: str, return_product_id: int) -> dict[str, Any]:
        with self.session_maker() as session:
            stmt = (
                insert(Products)
                .values(
                    odoo_product_id=opid,
                    product_name=name,
                    barcode=barcode, 
                    product_return_id=return_product_id
                )
                .returning(Products.product_id))
            res = session.execute(stmt).fetchone()._asdict()
            session.commit()
        return res

    def add_product_return(self, opid: int, name: str, returnable: bool, return_value: float) -> dict[str, Any]:
        with self.session_maker() as session:
            stmt = (
                insert(Product_returns)
                .values(
                    odoo_product_return_id=opid,
                    product_return_name=name,
                    returnable=returnable,
                    return_value=return_value
                )
                .returning(Product_returns.product_return_id)
            )
            res = session.execute(stmt).fetchone()._asdict()
            session.commit()
        return res

    def update_deposit_barcode(self, deposit_id: int, ean: str, barcode_base_id: int) -> None:
        with self.session_maker() as session:
            stmt = (
                update(Deposits)
                .values(deposit_barcode=ean, 
                        deposit_barcode_base_id=barcode_base_id
                )
                .where(Deposits.deposit_id == deposit_id)
            )
            session.execute(stmt)
            session.commit()

    def update_deposit_redeem(self, deposit_id: int, redeem_id: int) -> None:
        with self.session_maker() as session:
            stmt = (
                update(Deposits)
                .values(redeemed==redeem_id)
                .where(Deposits.deposit_id == deposit_id)
            )
            session.execute(stmt)
            session.commit()

    def get_product_from_opid(self, opid: int) -> dict[str, Any]: 
        with self.session_maker() as session:
            stmt = (
                select(Products)
                .where(Products.odoo_product_id == opid)
            )
            res = session.execute(stmt)
        return self._collect(res, "one")

    def get_return_product_from_opid(self, opid: int) -> dict[str, Any]: 
        with self.session_maker() as session:
            stmt = (
                select(Product_returns)
                .where(Product_returns.odoo_product_return_id == opid)
            )
            res = session.execute(stmt)
        return self._collect(res, "one")

    # DEPOSITS
    def add_deposit(self, receiver_id: int, provider_id: int) -> dict[str,Any]:
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
                .returning(Deposits.deposit_id)
            )
            res = session.execute(stmt).fetchone()._asdict()
            session.commit()
        return res


    def close_deposit(self, deposit_id: int) -> None:
        with self.session_maker() as session:
            stmt = (
                update(Deposits)
                .values(close=True)
                .where(Deposits.deposit_id == deposit_id)
            )
            session.execute(stmt)
            session.commit()

    def add_deposit_line(self, deposit_id: int, product_id: int, canceled: bool=False) -> dict[str,Any]:
        with self.session_maker() as session:
            stmt = (
                insert(Deposit_lines)
                .values(
                    deposit_id=deposit_id,
                    product_id=product_id,
                    deposit_line_datetime=datetime.now().isoformat("-"),
                    canceled=canceled,
                )
                .returning(Deposit_lines.deposit_line_id)
            )
            res = session.execute(stmt).fetchone()._asdict()
            session.commit()
        return res

    def cancel_returned_product(self, deposit_id: int, deposit_line_id:int) -> None:
        with self.session_maker() as session:
            stmt = (
                update(Deposit_lines)
                .values(canceled=True)
                .where(Deposit_lines.deposit_id == deposit_id)
                .where(Deposit_lines.deposit_line_id == deposit_line_id)
            )
            session.execute(stmt)
            session.commit()


    # GLOBAL
    def get_first_deposit_datetime(self) -> str|None:
        with self.session_maker() as session:
            stmt = (
                select(Deposits)
                .where(Deposits.deposit_id == 1)
            )
            deposit = self._collect(session.execute(stmt), "one")
            if deposit is None:
                return
            return deposit.get("deposit_datetime")

    def get_last_redeem_datetime(self) -> str|None:
        with self.session_maker() as session:
            stmt = (
                select(Redeem)
                .order_by(Redeem.redeem_id.desc())
                .limit(1)
            )
            redeem = self._collect(session.execute(stmt), "one")
            if redeem is None:
                return
            return redeem.get("redeem_datetime")

    def get_tracked_consigne_barcodes_bases(self) -> list[str]:
        with self.session_maker() as session:
            stmt = (
                select(Consigne.consigne_barcode_base)
                .select_from(Consigne)
            )
            redeem = self._collect(session.execute(stmt), "all")
        return [r.get("consigne_barcode_base") for r in redeem]


    def get_deposit_data(self, deposit_id: int) -> dict[str,Any]|None:
        with self.session_maker() as session:
            stmt = (
                select(Deposits)
                .where(Deposits.deposit_id == deposit_id)
            )
            deposit = self._collect(session.execute(stmt), "one")
            if deposit is None:
                return deposit
            
            receiver_id = deposit.get("reciever_id")
            provider_id = deposit.get("provider_id")

            reciever_stmt = (
                Select(Users)
                .where(Users.user_id == receiver_id)
            )
            provider_stmt = (
                Select(Users)
                .where(Users.user_id == provider_id)
            )

            receiver = self._collect(session.execute(reciever_stmt),"one")
            provider = self._collect(session.execute(provider_stmt),"one")

            stmt = (    
                select(Deposit_lines, Products, Product_returns)
                .select_from(Deposit_lines)
                .join(Products)
                .join(Product_returns)
                .where(Deposit_lines.deposit_id == deposit_id)
            )
            deposit_lines = self._collect(session.execute(stmt), "all")

        return {
            "deposit": deposit,
            "provider": provider,
            "receiver": receiver,
            "deposit_lines": deposit_lines
        }


    def get_deposit_line_data(self, deposit_id: int, deposit_line_id: int) -> dict[str, Any]:
        with self.session_maker() as session:
            stmt = (
                select(Deposit_lines)
                .join(Products)
                .join(Product_returns)
                .where(Deposit_lines.deposit_id == deposit_id)
                .where(Deposit_lines.deposit_line_id == deposit_line_id)
            )
            res = session.execute(stmt)
        return self._collect(res, "one")

    def get_returns_per_types(self, deposit_id) -> list[tuple[str, int, float]]:
        RETURNS_PER_PRODUCT_TYPE = """\
            SELECT 
                product_returns.product_return_name, 
                COUNT(deposit_line_id), 
                ROUND(SUM(product_returns.return_value), 2)
            FROM deposit_lines 
            JOIN products ON deposit_lines.product_id=products.product_id 
            JOIN product_returns ON products.product_return_id=product_returns.product_return_id 
            WHERE 
                deposit_id = :did
                AND canceled = 0 
                AND product_returns.product_return_id != 1
            GROUP BY products.product_return_id;
            """

        with self.session_maker() as session:
            res = session.execute(text(RETURNS_PER_PRODUCT_TYPE), {'did':deposit_id}).fetchall()
        return res

    # REDEEM
    def match_redeem_deposits(self, barcode: str, partner_id: int, value: float) -> dict[str, Any] | None: 
        POS_REDEEM_MATCHING = """\
            SELECT 
                deposits.deposit_id,
                ROUND(SUM(product_returns.return_value), 2)
            FROM deposits
            JOIN deposit_lines ON deposit_lines.deposit_id=deposits.deposit_id
            JOIN users ON users.user_id=deposits.receiver_id as rc
            JOIN products ON deposit_lines.product_id=products.product_id 
            JOIN product_returns ON products.product_return_id=product_returns.product_return_id 
            WHERE
                deposits.deposit_barcode = :barcode
                AND rc.user_partner_id = :pid
                AND sum = :value
                AND deposit.closed = 1
            GROUP BY deposits.deposit_id
            ORDER BY deposit_id
            """
        with self.session_maker() as session:
            res = session.execute(text(POS_REDEEM_MATCHING), {'pid':partner_id, "barcode": barcode, "value": value}).fetchall()
        return res

    def add_redeem(self, order_id: int, dt: str, user_id: int, value: float, barcode: str, anomaly: bool) -> dict[str, Any]:
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
                .returning(Redeem.redeem_id)                
            )
            res = session.execute(stmt).fetchone()._asdict()
            session.commit()
        return res
    
    def _update_consigne_barcodes(self, records: tuple) -> None:
        with self.session_maker() as session:
            stmt = (
                select(Consigne.consigne_barcode_base)
                .select_from(Consigne)
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
                        .where(Consigne.consigne_barcode_base == base)
                    )
                    session.execute(stmt)
            session.commit()


    def next_barcode_base(self) -> tuple[int, str]:
        with self.session_maker() as session:
            stmt = (
                select(Deposits.deposit_barcode_base_id)
                .where(Deposits.deposit_barcode_base_id != None)
                .order_by(Deposits.deposit_id.desc())
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
        

    def _get_base(self, consigne_id: int) -> int|None:
        with self.session_maker() as session:
            stmt = (
                select(Consigne.consigne_barcode_base)
                .select_from(Consigne)
                .where(Consigne.consigne_id == consigne_id)
            )
            res = session.execute(stmt).fetchone()
        if res:
            return res[0]
        return res
