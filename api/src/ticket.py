from __future__ import annotations

from pathlib import Path
from PIL.Image import Image
from barcode.ean import EAN13
from barcode.writer import ImageWriter

from typing import Any

from src.database import ConsigneDatabase


"""
BARCODE RULE EAN13: 999....{NNNDD}

"""

StrOrPath = str | Path
DepositRecord = dict[str, Any]
DepositLinesRecords = list[dict[str, Any]]

DIMENSION = ((23, 69))

class DepositBarcode(object):
    deposit_value: float
    ean: str

    def __init__(self, deposit_value: float):
        if deposit_value > 100:
            raise ValueError("Deposit Value Too high")
        self.deposit_value = deposit_value

    @property
    def ean(self) -> str:
        """apply ean generating rule in deposit value."""
        return ...

    def generate(self, fp: StrOrPath):
        """Generate barcode png into fp"""
        _writer = ImageWriter()
        img = EAN13(self.ean, _writer).render()
        img = self._resize(img, DIMENSION)
        img.save(fp)

    def _resize(self,img:Image, dimensions: tuple[int, int | None]) -> Image:
        if dimensions[1] is None:
            dimensions = (dimensions[0], img.size[1])
        return img.resize(dimensions)

class DepositTicket(object):
    deposit: dict[str, Any]
    deposit_lines: list[dict[str, Any]]
    barcode: DepositBarcode

    def __init__(self,  outfile: StrOrPath) -> None:
        self.outfile = Path(outfile)

    @classmethod
    def from_database(self, deposit_id: int, database: ConsigneDatabase) -> DepositTicket:
        ...
    
    def render(self, deposit: DepositRecord,  deposit_lines: DepositLinesRecords) -> str:
        ...

    def ticket_value(self, deposit_lines: DepositLinesRecords) -> float:
        ...