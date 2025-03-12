from __future__ import annotations
from contextlib import ContextDecorator
from escpos.printer import Usb, Network

from datetime import datetime
from functools import reduce
import re
import random
from collections import deque

from typing import Any

"""
BARCODE RULE EAN13: 999....{NNNDD}

"""

class ConsignePrinter(object):
    host: str
    profile: str
    options: dict[str, Any]
    def __init__(self, host: str, profile: str, **kwargs):
        self.host = host
        self.profile = profile
        self.options = kwargs

    def make_printer_session(self) -> DepositTicket:
        return DepositTicket(self.host, profile=self.profile, **self.options)


class DepositTicket(Network, ContextDecorator):
    BARCODE_RULE: str = "999....NNNDD"
    RETURN_LINE: str = "{quantity:<3d}X {name:.<20s}: {value:3.1f}€\n"
    TOTAL_LINE: str =  "Total{name:.<20s}: {value:3.1f}€\n"

    def __init__(self, host = "", port = 9100, timeout = 60, *args, **kwargs):
        super().__init__(host, port, timeout, *args, **kwargs)

    def __enter__(self):
        if not all([self.is_usable(), self.is_online()]):
            raise ValueError("Unable to dialogue with the printer.")
        return self

    def __exit__(self, exc_type, exc, exc_tb):
        self.cut()
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