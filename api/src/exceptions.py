from sanic import SanicException


class ConsigneException(SanicException):
    ...



class SameUserError(ConsigneException):
    status_code: int = 500
    internal_error_id: int = 0
    message: str = "A Provider user is not allowed to do it's own returns."

    def __init__(self) -> None:
        super().__init__(self.message)

