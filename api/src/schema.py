from sqlalchemy import JSON, Column, DateTime, Integer, UnicodeText, Numeric, Enum, Boolean, Sequence, ForeignKey, BOOLEAN, REAL
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base

from typing import Any

def _values(self) -> dict[str, Any]:
    values = self.__dict__
    values.pop("_sa_instance_state", None)
    return values

Base = declarative_base()
Base._values = _values


class Users(Base):
    __tablename__ = "users"
    __table_args__ = {"schema": "main"}

    user_id = Column(Integer, primary_key=True, autoincrement=True)
    user_partner_id = Column(Integer, unique=True)
    user_code = Column(Integer, unique=True)
    user_name = Column(UnicodeText, nullable=False)
    last_provider_activity = Column(UnicodeText)
    last_receiver_activity = Column(UnicodeText)

class Redeem(Base):
    __tablename__ = "redeem"
    __table_args__ = {"schema": "main"}

    redeem_id = Column(Integer, primary_key=True, autoincrement=True)
    odoo_pos_id = Column(Integer, nullable=False)
    redeem_datetime = Column(UnicodeText, nullable=False)
    redeem_user = Column(Integer, ForeignKey("main.users.user_id"), nullable=False)
    redeem_value = Column(REAL, nullable=False)
    redeem_barcode = Column(UnicodeText, nullable=False)
    anomaly = Column(BOOLEAN, nullable=False)

class Consigne(Base):
    __tablename__ = "consigne"
    __table_args__ = {"schema": "main"}

    consigne_id = Column(Integer, primary_key=True, autoincrement=True)
    consigne_pattern = Column(UnicodeText)
    consigne_name = Column(UnicodeText)
    consigne_barcode = Column(UnicodeText, unique=True)
    consigne_barcode_base = Column(UnicodeText)
    consigne_active = Column(BOOLEAN)

class Product_returns(Base):
    __tablename__ = "product_returns"
    __table_args__ = {"schema": "main"}

    product_return_id = Column(Integer, primary_key=True, autoincrement=True)
    odoo_product_return_id = Column(Integer, unique=True)
    product_return_name = Column(UnicodeText, nullable=False)
    returnable = Column(BOOLEAN, nullable=False)
    return_value = Column(REAL)

class Products(Base):
    __tablename__ = "products"
    __table_args__ = {"schema": "main"}

    product_id = Column(Integer, primary_key=True, autoincrement=True)
    odoo_product_id = Column(Integer, unique=True, nullable=False)
    product_name = Column(UnicodeText, nullable=False)
    barcode = Column(UnicodeText, nullable=False)
    product_return_id = Column(Integer, ForeignKey("main.product_returns.product_return_id"))

class Deposits(Base):
    __tablename__ = "deposits"
    __table_args__ = {"schema": "main"}

    deposit_id = Column(Integer, primary_key=True, autoincrement=True)
    receiver_id = Column(Integer, ForeignKey("main.users.user_id"), nullable=False)
    provider_id = Column(Integer, ForeignKey("main.users.user_id"), nullable=False)
    deposit_datetime = Column(UnicodeText, nullable=False)
    closed = Column(BOOLEAN, nullable=False)
    deposit_barcode = Column(UnicodeText)
    deposit_barcode_base_id = Column(Integer, ForeignKey("main.consigne.consigne_id"))
    redeemed = Column(Integer, ForeignKey("main.redeemed.redeem_id"))



class Deposit_lines(Base):
    __tablename__ = "deposit_lines"
    __table_args__ = {"schema": "main"}

    deposit_line_id = Column(Integer, primary_key=True, autoincrement=True)
    deposit_id = Column(Integer, ForeignKey("main.deposits.deposit_id"), nullable=False)
    product_id = Column(Integer, ForeignKey("main.products.product_id"), nullable=False)
    deposit_line_datetime = Column(UnicodeText, nullable=False)
    canceled = Column(Boolean, nullable=False)