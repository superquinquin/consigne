

from sanic import Request, Blueprint, HTTPResponse
from sanic.response import json

from src.engine import ConsigneEngine

consigneBp = Blueprint("consigneBp", url_prefix="/")

@consigneBp.route("/auth_provider", methods=["POST"])
async def provider_login(request: Request) -> HTTPResponse:
    """
    provide a way to authenticate an user with odoo credentials.
    POST {"username":str, "password": str}
    

    :return: a json payload
        auth(bool): is the auth successful
        user(dict|None): 
            user_name(str): name of the user
            user_code(str): user barcode_base (account number)

            user payload is None when auth is failed. otherwise     
    """
    payload = request.load_json()
    username = payload.get("username", None)
    password = payload.get("password", None)
    print(username, password)
    if not all([username, password]):
        raise KeyError("Missing `username` or `password`")

    engine: ConsigneEngine = request.app.ctx.engine
    res = engine.authenticate_provider(username, password)
    return json({"status": 200, "reasons": "OK", "data": res})

@consigneBp.route("/deposit/create", methods=["POST"])
async def initialize_return(request: Request) -> HTTPResponse:
    """Provide a way to generate a new deposit.
    a `code` is the member account number. odoo model.field: `res.partner.barcode_base`

    For creating a new deposit, it is necessary to provide a receiver_code and a provider_code.
        where receiver_code is the barcode_base of the person returning the products.
        where provider_code is the barcode_base of the person providing the returning service.
    
    POST payload: {provider_code: int, receiver_code: int}


    :return: a json paylaod
        deposit_id(int): the deposit id you just created.
    """

    payload = request.load_json()
    provider_code = payload.get("provider_code", None)
    receiver_code = payload.get("receiver_code", None)
    if not all([provider_code, receiver_code]):
        raise KeyError("Missing `provider_code` or `receiver_code`")

    engine: ConsigneEngine = request.app.ctx.engine
    res = engine.initialize_return(receiver_code, provider_code)
    return json({"status": 200, "reasons": "OK", "data": {"deposit_id": res}})

@consigneBp.route("/deposit/<deposit_id:int>", methods=["GET"])
async def get_deposit(request: Request, deposit_id: int) -> HTTPResponse:
    """Get a json payload of a requested deposit
    
    :return: json payload:
        deposit(dict): desposit record
        receiver(dict): receiver user record
        provider(dict): provider user record
        deposit_lines(list[dict]): list of all deposit_lines
    """
    engine: ConsigneEngine = request.app.ctx.engine
    res = engine.get_deposit_data(deposit_id)
    return json({"status": 200, "reasons": "OK", "data": res})

@consigneBp.route("/deposit/<deposit_id:int>/<deposit_line_id:int>", methods=["GET"])
async def get_deposit_line(request: Request, deposit_id: int, deposit_line_id: int) -> HTTPResponse:
    """Get a json payload of a requested deposit_line.
    you must provide an existing combinaison of `deposit_id` and `deposit_line_id`
    
    :return: json payload:
        deposit_lines(dict): a deposit_lines record
    """
    engine: ConsigneEngine = request.app.ctx.engine
    res = engine.get_deposit_line_data(deposit_id, deposit_line_id)
    return json({"status": 200, "reasons": "OK", "data": res})

@consigneBp.route("/deposit/<deposit_id:int>/return/<product_barcode:str>", methods=["GET"])
async def get_product(request: Request, deposit_id: int, product_barcode: str) -> HTTPResponse:
    """provide a way to return a scanned product during a deposit.
    from scanned product barcode. verify product returnability and potential value.

        :return: Json Payload (among other return fields...)
            Returnable product:
                returnable(bool): is true when a product can be returned
                return_value(float): Is > 0 when returnable. 
                    Define the value that must be handed to the receiver for this very product return 
                
            NON Returnable product:
                returnable(bool): is False when a product cannot be returned
                return_value(float|None): Backend set the return value to 0.0. Likely to be interpreted as None from the frontend. 
    """
    engine: ConsigneEngine = request.app.ctx.engine
    res = engine.return_product(deposit_id, product_barcode)
    return json({"status": 200, "reasons": "OK", "data": res})

@consigneBp.route("/deposit/<deposit_id:int>/cancel/<deposit_line_id:int>", methods=["GET"])
async def cancel_returned_product(request: Request, deposit_id: int, deposit_line_id: str) -> HTTPResponse:
    """Cancel a the deposit_line of a returned product.
    the `deposit_id` & `deposit_line_id` path argument combinaison must be valid.
    """

    engine: ConsigneEngine = request.app.ctx.engine
    res = engine.cancel_deposit_line(deposit_id, deposit_line_id)
    return json({"status": 200, "reasons": "OK", "data": {}})

@consigneBp.route("/deposit/<deposit_id:int>/ticket", methods=["GET"])
async def get_ticket(request: Request, deposit_id: int) -> HTTPResponse:
    """Request to generate a ticket for a given deposit."""
    raise NotImplementedError()

