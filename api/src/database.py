from __future__ import annotations

import json
from enum import Enum
from attrs import define, field, validators
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime

from sqlite3 import PARSE_DECLTYPES
from sqlite3 import Cursor, Row, Connection
from sqlite3 import connect, register_adapter, register_converter

from typing import Any, Literal, Sequence

from collections import deque

StrOrPath = str | Path
Conditions = list[tuple[str, str, Any]]

FK_ON = "PRAGMA foreign_keys=ON;"
CASE_SENSITIVE_ON = "PRAGMA case_sensitive_like=ON;"
TABLE_NAMES = "SELECT name FROM sqlite_master WHERE type='table';"
TABLE_INFO = "PRAGMA table_info({table_name});"
FK_INFO = "PRAGMA foreign_key_list({table_name});"

WRITE = "INSERT {on_conflict} INTO {table_name}({columns}) VALUES({values}) {returning};"
UPDATE = "UPDATE {table_name} SET {setter} {conditions};"
DELETE = "DELETE FROM {table_name} {conditions};"
READ_ONE = "SELECT {fields} FROM {table_name} {joins} {conditions} {order} {axis};"
READ_MANY = "SELECT {fields} FROM {table_name} {joins} {conditions} {order} {axis} {limit};"


class SqlExtraDtypes(str, Enum):
    DATETIME = "DATETIME"
    JSON = "JSON"
    JSONLIST = "JSONLIST"

class SqlOperator(str, Enum):
    Eq = "="
    Diff = "!="
    Glob = "GLOB"
    Gt = ">"
    Ge = ">="
    Ngt = "!>"
    Lt = "<"
    Le = "<="
    Nlt = "!<"
    Like = "LIKE"
    Ilike = "ILIKE"
    In = "IN"
    Not_in = "NOT IN"
    Is = "IS"
    Is_not = "IS NOT"

    def values():
        return [s.value for s in SqlOperator]

class OnConflict(str, Enum):
    Update = "update"
    Ignore = "ignore"
    Rollback = "rollback"
    Abort = "abort"
    Fail = "fail"
    Replace = "replace"
    NONE = "none"

    def sql(self) -> str:
        if self.value == "none":
            return ""
        return f"OR {str(self).upper()}"

def intOrNone(instance, attribute, value):
    if value is None:
        return
    if not isinstance(value, int):
        raise TypeError(f"attribute {attribute} must be of type int.")

def listOrNone(instance, attribute, value):
    if value is None:
        return
    if not isinstance(value, list):
        raise TypeError(f"attribute {attribute} must be of type list.")

def onConflictOrNone(instance, attribute, value):
    if value is None:
        return
    if not isinstance(value, OnConflict):
        raise TypeError(f"attribute {attribute} must be of type OnConflict.")

@dataclass(frozen=True)
class FKRelation(object):
    table: str
    table_field: str
    related_table: str
    related_table_field: str

    @property
    def join(self) -> str:
        return f"JOIN {self.related_table} ON {self.table}.{self.table_field} = {self.related_table}.{self.related_table_field}"

@dataclass(frozen=True)
class Field(object):
    name: str
    dtype: str

    @classmethod
    def from_pragma(cls, pragma: tuple) -> Field:
        return cls(pragma[1], pragma[2])

@dataclass(frozen=True)
class Schema(object):
    name: str
    fields: dict[str, Field]
    relations: dict[str, FKRelation]
    
    @classmethod
    def from_pragma(cls, name: str, pragma: list[tuple]) -> Schema:
        fields = {info[1]:Field.from_pragma(info) for info in pragma}
        return cls(name, fields, {})
    
    def is_joingnable(self, table_name: str) -> bool: 
        table = self.relations.get(table_name, None)
        return bool(table)
    
    def join(self, table_name: str) -> str:
        if self.is_joingnable(table_name) is False:
            raise ValueError(f"{table_name} cannot be joined")
        table = self.relations.get(table_name)
        return table.join()

@define(kw_only=True, slots=False, frozen=True)
class Namespace:
    table: str = field(validator=[validators.instance_of(str)])
    fname: str = field(validator=[validators.instance_of(str)])
    dtype: str = field(validator=[validators.instance_of(str)])

    @classmethod
    def from_pragma(cls, table_name: str, pragma: tuple) -> Namespace:
        return cls(table=table_name, fname=pragma[1], dtype=pragma[2])

    def select(self) -> str:
        return f"{self.table}.{self.fname}"

    def where(self, op: str, values: Any) -> tuple[str, Any]:
        fname, op, values = self._prepare(op, values)
        return ((f"{fname} {op} {self._set_anchor(op, values)}", values))

@define(kw_only=True)
class SimpleSqlConverter:
    namespaces: dict[str, Namespace] = field()
    schemas: dict[str, Schema] = field()
    
    table_name: str | None = field(default=None)
    fields: list[str] | None = field(default=None)
    
    on_conflict: OnConflict|None = field(default=None, validator=[onConflictOrNone])
    values: list[Any]|list[list[Any]]|None = field(default=None, validator=[listOrNone])
    setter: list[tuple[str, Any]] | None = field(default=None)
    limit: int | None = field(default=None, validator=[intOrNone])
    order_by: list[str] | None = field(default=None, validator=[listOrNone])
    axis: int = field(default=1, converter=int, validator=[validators.instance_of(int)])
    returning: list[str] | None = field(default=None)

    # keep conditions simple
    conditions: Conditions | None = field(default=None, validator=[listOrNone])


    def write(self) -> tuple[str, list[Any]]: 
        """write and write many, depending wether values is list or list[list]"""
        if not all([self.table_name, self.fields, self.values, self.on_conflict]):
            raise ValueError("Missing arguments.")

        stmt = WRITE.format(
                table_name= self.table_name,
                column=self._parse_fields(),
                values=self._anchors(self.values),
                on_conflict=self.on_conflict,
                returning=self._parse_returning()
            )
        return (stmt, self.values)

    def update(self) -> tuple[str, list[Any]]: 
        if not all([self.table_name, self.setter]):
            raise ValueError("Missing arguments.")

        setter, svalues = self._parse_setter()
        conditions, cvalues = self._parse_conditions()
        values = svalues + cvalues

        stmt = UPDATE.format(
            table_name=self.table_name,
            setter = setter,
            conditions=conditions
        )
        return (stmt, values)


    def delete(self) -> tuple[str, list[Any]]: 
        conditions, values = self._parse_conditions()
        stmt = DELETE.format(
            table_name=self.table_name,
            conditions=conditions
        )
        return (stmt, values)

    def read_one(self) -> tuple[str, list[Any]]:
        fields = self._parse_fields()
        conditions, values = self._parse_conditions()
        joins = self._parse_join()
        order_by = self._parse_order()
        axis = self._parse_axis()
        stmt = READ_ONE.format(
            fields=fields,
            table_name=self.table_name,
            joins=joins,
            conditions=conditions,
            order=order_by,
            axis=axis
        )
        return (stmt, values)

    def read_many(self) -> tuple[str, list[Any]]:
        fields = self._parse_fields()
        conditions, values = self._parse_conditions()
        joins = self._parse_join()
        order_by = self._parse_order()
        axis = self._parse_axis()
        limit = self._parse_limit()
        stmt = READ_MANY.format(
            fields=fields,
            table_name=self.table_name,
            joins=joins,
            conditions=conditions,
            order=order_by,
            axis=axis,
            limit=limit
        )
        return (stmt, values)

    def _parse_join(self) -> str:
        def _parse_sequence(sequence: list[str]|Conditions|None) -> list[str]:
            if sequence is None or len(sequence) == 0:
                return []
            if isinstance(sequence[0], Sequence) and not isinstance(sequence[0], str):
                fields = [s[0] for s in sequence] # considering simple conditions formating
            buff = []
            for fname in fields:
                if fname == "*":
                    continue
                namespace = self.namespaces.get(fname, None)
                if namespace is None:
                    raise ValueError(f"Unknown field name: {fname}")
                table = self.schemas.get(namespace.table)
                buff.append(table)
            return buff

        tables_to_join, join, joined_tables = [], [], [self.table_name]

        [tables_to_join.extend(_parse_sequence(s)) for s in [self.fields, self.order_by, self.conditions]]
        tables_to_join = deque(list(set(tables_to_join)))

        loop_size, joined_size, iter_number = len(tables_to_join), len(joined_tables), 0
        while len(tables_to_join) > 0:
            table = tables_to_join.popleft()

            _joined, inplace_table_names = False, deque(joined_tables)
            while _joined is False or len(inplace_table_names) == 0:
                inplace_table_name = inplace_table_names.popleft()
                inplace_table = self.schemas.get(inplace_table_name, None)

                if inplace_table is None:
                    raise ValueError(f"Unknown table: {table.name}")
                
                if table.is_joingnable(inplace_table.name):
                    join.append(table.join(inplace_table))
                    joined_tables.append(table)
                    _joined = True

            if _joined is False:
                tables_to_join.append(table)

            iter_number += 1
            if iter_number == loop_size:
                loop_size, iter_number = len(tables_to_join), 0
                if joined_size == len(joined_size):
                    break
                joined_size = len(joined_tables)

        if len(tables_to_join) > 0:
            raise ValueError(f"all tables are not joignable.")
        return " ".join(join)

    def _parse_conditions(self) -> tuple[str, list[Any]]:
        if self.conditions is None:
            return ("", [])

        schema = self.schemas.get(self.table_name, None)
        if schema is None:
            raise ValueError(f"Unknown table name: {self.table_name}.")

        values, conditions = [], []
        for field, op, val in self.conditions:
            namespace = self.namespaces.get(field, None)
            if op not in SqlOperator.values():
                raise ValueError(f"Unknown operator: {op}.")
            if namespace is None:
                raise ValueError(f"Unknown {self.table_name} field: {field}")

            where, val = namespace.where(op, val)
            conditions.append(where)
            if isinstance(val, list):
                values.extend(val)
            else:
                values.append(val)
        return ("WHERE " + ' AND '.join(conditions), values)

    def _parse_setter(self, set_values: list[tuple[str, Any]]) -> tuple[str, Any]:
        values, fields = [], []
        for fname, val in set_values:
            namespace = self.namespaces.get(fname, None)
            if namespace is None:
                raise KeyError(f"Unknown field name: {fname}")
            fields.append(f"{fname} = ?")
            values.append(val)
        return (", ".join(fields), values)

    def _parse_fields(self) -> str:
        fields = ["*"]
        if self.fields is not None:
            fields = []
            for fname in self.fields:
                namespace = self.namespaces.get(fname, None)
                if namespace is None:
                    raise KeyError(f"Unknown field name: {fname}")
                fields.append(namespace.select())
        return ", ".join(fields)

    def _parse_conflict_handling(self) -> str:
        handler = ""
        if self.on_conflict is not None:
            handler = self.on_conflict.sql()
        return handler

    def _parse_limit(self) -> str:
        limit = ""
        if self.limit is not None:
            limit = f"LIMIT {str(self.limit)}"
        return limit

    def _parse_order(self) -> str:
        if self.order_by is None:
            return ""
        f = ", ".join([self.namespaces[fname].select() for fname in self.order_by])
        return f"ORDER BY {f}"

    def _parse_axis(self) -> str:
        if self.order_by is None:
            return ""
        match self.axis:
            case 1:
                return "ASC"
            case 0:
                return "DESC"
            case _:
                raise ValueError("Axis must be either 1 or 0")

    def _parse_returning(self) -> str:
        if self.returning is None:
            return ""
        
        returning = []
        for field in self.returning:
            namespace = self.namespaces.get(field, None)
            if namespace is None:
                raise ValueError(f"Unknown field: {field}")
            returning.append(namespace.select())
        return ", ".join(returning)

    @staticmethod
    def _condition_anchors(op: str, values: Any) -> str:
        """define the right anchor for the given condition operator."""
        anchor = "?"
        if op.lower() == "in" and isinstance(values, list):
            anchors = ' ,'.join(["?" for _ in range(len(values))])
            anchor = f"({anchors})"
        return anchor

    @staticmethod
    def _anchors(values: list[Any]) -> str:
        return ' ,'.join(["?" for _ in range(len(values))])





class LiteORM:
    con: Connection
    cursor: Cursor
    schemas: dict[str, Schema]
    namespaces: dict[str, Namespace]
    path: str
    params: dict[str, Any]
    timeout: int
    
    def __init__(self, path: str = ":memory:", timeout: int = 5, **params):
        self.path = path
        self.params = params
        self.timeout = timeout

        self.con = connect(self.uri, detect_types=PARSE_DECLTYPES, uri=True, timeout=timeout)
        self.cursor = self.con.cursor()

        self.con.execute(FK_ON)
        self.con.execute(CASE_SENSITIVE_ON)
        self.con.row_factory = self._record_factory

        self._load_schemas()
        if len(self.schemas.keys()) == 0:
            raise ValueError("Consigne database not found. Please run Schema.sql to first create Consigne database.")

        register_adapter(list, self._json_serializer)
        register_adapter(dict, self._json_deserializer)
        register_adapter(datetime, self._datetime_serializer)
        register_converter(SqlExtraDtypes.JSON.value, self._json_deserializer)
        register_converter(SqlExtraDtypes.JSONLIST.value, self._json_deserializer)
        register_converter(SqlExtraDtypes.DATETIME.value, self._datetime_deserializer)

    @property
    def uri(self) -> str:
        options = ""
        if bool(self.params):
            options = "?" + "&".join([f"{k}={v}" for k,v in self.params.items()])
        return f"file:{self.path}{options}"

    def write_one(
        self, 
        table_name: str, 
        columns: list[str], 
        values: list[Any],
        returning: list[str]|None = None, 
        on_conflict:OnConflict=OnConflict.Ignore, 
        commit: bool=True
    ) -> list[Any]|None:      
        stmt, payload = SimpleSqlConverter(
            schemas=self.schemas,
            namespaces=self.namespaces,
            table_name=table_name,
            fields=columns,
            values=values,
            on_conflict=on_conflict,
            returning=returning
        )
        return self._execute(stmt, payload, commit)

    def write_many(
        self, 
        table_name: str, 
        columns: list[str], 
        values: list[list[Any]], 
        returning: list[str]|None = None,
        on_conflict:OnConflict=OnConflict.Ignore, 
        commit: bool=True
    ) -> list[Any]|None:
        stmt, payload = SimpleSqlConverter(
            schemas=self.schemas,
            namespaces=self.namespaces,
            table_name=table_name,
            fields=columns,
            values=values,
            on_conflict=on_conflict,
            returning=returning
        ).write()
        return self._execute_many(stmt, payload, commit)

    def update(
        self, 
        table_name: str, 
        setter: list[tuple[str, Any]], 
        conditions: list[str, str, Any], 
        commit: bool= True
    ) -> None: 
        stmt, payload = SimpleSqlConverter(
            schemas=self.schemas,
            namespaces=self.namespaces,
            table_name=table_name,
            setter=setter,
            conditions=conditions
        ).update()
        return self._execute(stmt, payload, commit)

    def delete(
        self, 
        table_name: str, 
        conditions: list[str, str, Any], 
        commit: bool= True
    ) -> None: 
        stmt, payload = SimpleSqlConverter(
            schemas=self.schemas,
            namespaces=self.namespaces,
            table_name=table_name,
            conditions=conditions
        ).delete()
        return self._execute(stmt, payload, commit)

    def read_one(
        self,
        table_name: str,
        fields: list[str] | None = None,
        conditions: Conditions | None = None,
        order_by: list[str] | None = None,
        axis: int = 1
    ) -> dict[str, Any]: 
        stmt, payload = SimpleSqlConverter(
            schemas=self.schemas,
            namespaces=self.namespaces,
            table_name=table_name,
            conditions=conditions,
            fields=fields,
            order_by=order_by,
            axis=axis
        ).read_one()
        return self.con.execute(stmt, payload).fetchone()

    def read_many(
        self,
        table_name: str,
        fields: list[str] | None = None,
        conditions: Conditions | None = None,
        order_by: list[str] | None = None,
        limit: int | None = None,
        axis: int = 1,
    ) -> list[dict[str, Any]]:
        stmt, payload = SimpleSqlConverter(
            schemas=self.schemas,
            namespaces=self.namespaces,
            table_name=table_name,
            conditions=conditions,
            fields=fields,
            order_by=order_by,
            limit=limit,
            axis=axis
        ).read_many()
        return self.con.execute(stmt, payload).fetchall()
    
    def get_tables_names(self) -> list[str]:
        return [x[0] for x in self.cursor.execute(TABLE_NAMES).fetchall()]

    def get_table_info(self, table_name: str) -> list[tuple]:
        return self.cursor.execute(TABLE_INFO.format(table_name=table_name)).fetchall()

    def get_table_fk_info(self, table_name: str) -> list[tuple]:
        return self.cursor.execute(FK_INFO.format(table_name=table_name)).fetchall()

    def _execute(self, stmt: str, payload: list[Any], commit: bool=True) -> list[Any]|None:
        res = self.con.execute(stmt, payload).fetchall()
        if commit:
            self.con.commit()
        return res

    def _execute_many(self, stmt: str, payload: list[list[Any]], commit: bool=True) -> list[Any]|None:
        res = self.con.executemany(stmt, payload).fetchall()
        if commit:
            self.con.commit()
        return res

    def _load_schemas(self) -> None:
        schemas, namespaces, relations = {}, {}, []
        for name in self.get_tables_names():
            info = self.get_table_info(name)
            fk_info = self.get_table_fk_info(name)
            for fk in fk_info:
                _, _, related_table, table_field, related_field, _,_,_ = fk
                relations.append(FKRelation(name, table_field, related_table, related_field))

            for pragma in info:
                namespaces.update({pragma[1]: Namespace.from_pragma(name, pragma)})

            schema = Schema.from_pragma(name, info)
            schemas.update({name: schema})

        for relation in relations:
            table = schemas.get(relation.table)
            table.relations.update({relation.related_table:relation})
            related_table = schemas.get(relation.related_table)
            related_table.relations.update({relation.table:relation})

        self.schemas = schemas
        self.namespaces = namespaces

    @staticmethod
    def _record_factory(cursor: Cursor, row: Row) -> dict[str, Any]:
        fields = [column[0] for column in cursor.description]
        return {k:v for k,v in zip(fields, row)}
    
    @staticmethod
    def _json_serializer(data: dict[str, Any] | list[Any]) -> str:
        return json.dumps(data)

    @staticmethod
    def _json_deserializer(data: str) -> dict[str, Any] | list[Any]:
        return json.loads(data)

    @staticmethod
    def _datetime_serializer(dt: datetime) -> dict[str, Any] | list[Any]:
        return dt.isoformat("-")

    @staticmethod
    def _datetime_deserializer(dt: str) -> dict[str, Any] | list[Any]:
        return datetime.fromisoformat(dt)
    


class ConsigneDatabase(LiteORM):
    def __init__(self, path = ":memory:", timeout = 5, **params):
        super().__init__(path, timeout, **params)

    def add_product(self, opid: int, name: str, barcode: str, returnable: bool, return_value: float|None=None) -> int:
        pid = self.write_one(
            "products",
            ["odoo_product_id", "product_name", "barcode", "returnable", "return_value"],
            [opid, name, barcode, returnable, return_value]
        )
        return pid

    def add_deposit(self, receiver_id: int, provider_id: int) -> int: 
        pid = self.write_one(
            "deposits",
            ["receiver_id", "provider_id", "deposit_datetime"],
            [receiver_id, provider_id, datetime.now()]
        )
        return pid
    
    def add_deposit_line(self, deposit_id: int, product_id: int, canceled: bool=False) -> int: 
        pid = self.write_one(
            "deposits_lines",
            ["deposit_id", "product_id", "deposit_line_datetime", "canceled"],
            [deposit_id, product_id, datetime.now(), canceled]
        )
        return pid
    
    def add_user(self, code: int) -> int:
        pid = self.write_one(
            "users",
            ["user_code", "last_provider_activity", "last_receiver_activity"],
            [code, None, None]
        )
        return pid

    def update_activity(self, code: int, activity_as: Literal["provider", "receiver"]) -> None:
        activity_field = f"last_{activity_as}_activity"
        self.update(
            "users",
            [(activity_field, datetime.now())],
            [("user_code", "=", code)]
        )

    def get_user(self, code: int) -> dict[str, Any] | None: ...
    def get_product(self, opid: int) -> dict[str, Any] | None: ...



if __name__ == "__main__":
    db =  ConsigneDatabase("database.db")
    print(db.namespaces)