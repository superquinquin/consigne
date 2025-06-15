import json
from hashlib import sha1
from datetime import datetime
from functools import wraps
from pymemcache.client.hash import HashClient

from typing import Any, Type


def cached_products(f):
    @wraps(f)
    def wrapper(engine, deposit_id: int, deposit_barcode: str) -> dict[str, Any]:
        cache: ConsigneCache = engine.cache
        if cache is None:
            return f(engine, deposit_id, deposit_barcode)

        res = cache.get(deposit_barcode)
        if res is None:
            res = f(engine, deposit_id, deposit_barcode)
            cache.cache_product(deposit_barcode, res)
        return res
    return wrapper

def cached_shifts(f):
    @wraps(f)
    def wrapper(engine) -> dict[str, Any]:
        cache: ConsigneCache = engine.cache
        if cache is None:
            current_zone, members = f(engine)
            return members

        zone = cache.get_shift_zone()
        members = cache.get("shift_users")

        now = datetime.now()
        if members is None or zone is None or now < zone.debut or now >= zone.end:
            current_zone, members = f(engine)
            cache.set_shift_zone(*current_zone)
            cache.set("shift_users", members, expire=86400)
        return members
    return wrapper

def cached_users(f):
    @wraps(f)
    def wrapper(engine, value: str) -> list[tuple[int, str]]:
        cache: ConsigneCache = engine.cache
        if cache is None:
            return f(engine, value)

        digest = sha1(value).hexdigest()
        res = cache.get(f"users_{digest}")
        if res is None:
            res = f(engine, value)
            cache.set(f"users_{digest}", res, expire=86400)
        return res
    return wrapper


class ConsigneCache(HashClient):
    def __init__(self, servers: list[tuple[str, int]], connect_timeout: int=5, timeout=5, encoding: str="utf-8"):
        super().__init__(
            servers, 
            serializer=self.serialize, 
            deserializer=self.deserialize, 
            connect_timeout=connect_timeout, 
            timeout=timeout,
            encoding=encoding
        )

    def get_shift_zone(self) -> Type|None:
        debut = self.get("shift_zone_debut")
        end = self.get("shift_zone_end")
        if not all([debut, end]):
            return None
        return Type("Zone", (object,), {"debut": debut, "end": end})

    def set_shift_zone(self, debut: datetime|None, end: datetime|None) -> None:
        self.set("shift_zone_debut", debut)
        self.set("shift_zone_end", end)

    def cache_product(self, barcode: str, payload: dict[str, Any], ttl: int = 86400) -> None:
        self.set(barcode, payload, expire=ttl)

    def serialize(self, key: str, value: Any) -> tuple[str, int]:
        if isinstance(value, str):
            return (value, 0)
        elif isinstance(value, datetime):
            return (value.isoformat(), 2)
        return (json.dumps(value), 1)
    
    def deserialize(self, key: str, value: str, flags: int) -> Any:
        if flags == 0:
            return value.decode(self.encoding)
        elif flags == 1:
            return json.loads(value)
        elif flags == 2:
            return datetime.fromisoformat(value.decode(self.encoding))
        raise Exception("Unknown serialization format")