from sanic import SanicException


class ConsigneException(SanicException):
    ...

class SameUserError(ConsigneException):
    status_code: int = 500
    internal_error_id: int = 0
    message: str = "Une personne ne peux pas faire ses propres retour de consignes"

    def __init__(self) -> None:
        super().__init__(self.message)

class AlreadyCLosedDepositPrintError(ConsigneException):
    status_code: int = 500
    internal_error_id: int = 1
    message: str = "Ce dépot de consigne à déjà été clos."

    def __init__(self) -> None:
        super().__init__(self.message)

class OdooError(ConsigneException):
    status_code: int = 500
    internal_error_id: int = 2

    def __init__(self, message: str) -> None:
        super().__init__(message)

class ProductNotFound(ConsigneException):
    status_code: int = 500
    internal_error_id: int = 3
    message: str = "Le produit scanné n'existe pas: {barcode}"

    def __init__(self, barcode: str) -> None:
        super().__init__(self.message.format(barcode=barcode))

class CoopNotFound(ConsigneException):
    status_code: int = 500
    internal_error_id: int = 4
    message: str = "Coopérateur inexistant ou désinscrit."

    def __init__(self) -> None:
        super().__init__(self.message)
