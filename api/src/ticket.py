from __future__ import annotations

import sys
from dataclasses import dataclass, field, asdict
from abc import ABC
from contextlib import ContextDecorator
from escpos.printer import Usb, Network

from datetime import datetime

from typing import Any, Optional, Type, Literal, get_args

"""
BARCODE RULE EAN13: 999....{NNNDD}

"""

Adapter = Literal["Usb", "Network"]


@dataclass(frozen=True)
class UsbSettings(object):
    profile: str = field()
    idVendor: Optional[int] | None = field(default=None)
    idProduct: Optional[int] | None = field(default=None)
    usb_args: Optional[dict[str, str|int]] | None = field(default=None)
    timeout: int = field(default=60)
    in_ep: Optional[int] = field(default=0x82) 
    out_ep: Optional[int] = field(default=0x01) 

@dataclass(frozen=True)
class NetworkSettings(object):
    host: str = field()
    profile: str = field()
    port: int = field(default=9100)
    timeout: int = field(default=60)
    
class ConsignePrinter(object):
    adapter: Adapter
    settings: UsbSettings|NetworkSettings

    def __init__(self, adapter: Adapter, settings: UsbSettings|NetworkSettings):
        self.adapter = adapter
        self.settings = settings

    @property
    def _adapter(self) -> Type[Usb|Network]:
        module = sys.modules.get(__name__)
        adapter = getattr(module, self.adapter, None)
        if adapter is None:
            raise ValueError(f"adapter must be either: [`Usb`, `Network`]")
        return adapter

    @property
    def _printer(self) -> Type[DepositTicket]:
        return type("Ticket", (DepositTicket, self._adapter), {})

    @classmethod
    def from_configs(cls, adapter: Adapter, settings: dict[str, Any]) -> ConsignePrinter:
        if adapter not in get_args(Adapter):
            raise ValueError(f"adapter must be either: [`Usb`, `Network`]")
        match adapter:
            case "Usb":
                printer_settings = UsbSettings(**settings)
            case "Network":
                printer_settings = NetworkSettings(**settings)
        return cls(adapter, printer_settings)

    def make_printer_session(self):
        return self._printer(**asdict(self.settings))

class DepositTicket(ABC, ContextDecorator):
    BARCODE_RULE: str = "999....NNNDD"
    RETURN_LINE: str = "{quantity:<3d}X {name:.<20s}: {value:3.1f}€\n"
    TOTAL_LINE: str =  "Total{name:.<20s}: {value:3.1f}€\n"

    def __enter__(self):
        if not all([self.is_usable(), self.is_online()]):
            raise ValueError("Unable to dialogue with the printer.")
        return self

    def __exit__(self, exc_type, exc, exc_tb):
        del self

    def print_ticket(
        self, 
        deposit_id: int,
        user_code: str, 
        user_name: str,
        returns_lines: list[tuple[str, int, float]],
        total_value: float,
        ean: str
    ):
        self._ticket_header(user_code, user_name)
        self._ticket_body(returns_lines, total_value)
        self._ticket_barcode(ean)
        self._ticket_footer(deposit_id)
        self.cut()

    def _ticket_header(self, user_code: str, user_name: str) -> None:
        self.set(align="center", bold=True, height=2, width=1, custom_size=True)
        self.text("CONSIGNE SUPERQUINQUIN FIVES\n")
        self.text("\n")

        self.set(align="left", bold=True, height=1, width=1, custom_size=True)
        self.text(f"{user_code} - {user_name}\n")
        self.text("\n")
    
    def _ticket_body(self, returns_lines: list[tuple[str, int, float]], total_value: float) -> None:
        self.set(align="left", bold=False, height=1, width=1, custom_size=True)
        for line in returns_lines:
            self.text(self._render_return_line(*line))
        self.text(self._render_total_line(total_value))
        self.text("\n")

    def _ticket_barcode(self, ean: str):
        self.set(align="center", bold=False)
        self.barcode(ean, 'EAN13', 100, 4, '', '')
        self.text("\n")

    def _ticket_footer(self, deposit_id: int) -> None:
        self.set(align="right", bold=False, height=1, width=1, custom_size=True)
        self.text(datetime.now().strftime("%d-%m-%Y %H:%M:%S") + "  " + str(deposit_id))

    def _render_return_line(self, name: str, quantity: int, value: float) -> str:
        if len(name) > 20:
            name = name[:17]
        return self.RETURN_LINE.format(name=name, quantity=quantity, value=value)

    def _render_total_line(self, value: float) -> str:
        return self.TOTAL_LINE.format(name="", value=value)

    def _troll_ticket(self) -> None:
        self.set(align="center", bold=True, height=2, width=2, custom_size=True)
        self.text("Bon pour une Bière gratuite !\n")
        self.text("\n")
        self.qr("https://www.youtube.com/watch?v=dQw4w9WgXcQ", size=10)
        self.cut()


@dataclass(frozen=True)
class RedeemAnaliserSettings:
    ...

@dataclass(frozen=True)
class PurchaseBehaviorSettings:
    ...

class Analyzer(object):
    redeem_settings: RedeemAnaliserSettings | None
    behevioral_settings: PurchaseBehaviorSettings | None

    def __init__(self, redeem_settings: RedeemAnaliserSettings, behavioral_settings: PurchaseBehaviorSettings):
        self.redeem_settings = redeem_settings
        self.behevioral_settings = behavioral_settings

    @classmethod
    def from_configs(cls, settings: dict[str, Any]) -> Analyzer:
        redeem = settings.get("redeem", None)
        if redeem:
            redeem = RedeemAnaliserSettings(**redeem)
        behavior = settings.get("behavior", None)
        if behavior:
            behavior = PurchaseBehaviorSettings(**behavior)
        return cls(redeem, behavior)
