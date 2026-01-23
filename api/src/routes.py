

from sanic import Request, Blueprint, HTTPResponse
from sanic.response import json, empty

from src.engine import ConsigneEngine

consigneBp = Blueprint("consigneBp", url_prefix="/")


@consigneBp.get("/favicon.ico")
async def favicon(_: Request):
    return empty()

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
    a `id` is the member id. odoo model.field: `res.partner.id`

    For creating a new deposit, it is necessary to provide a receiver_partner_id and a provider_partner_id.
        where receiver_partner_id is the partner_id of the person returning the products.
        where provider_partner_id is the partner_id of the person providing the returning service.
    
    POST payload: {provider_partner_id: int, receiver_partner_id: int}


    :return: a json paylaod
        deposit_id(int): the deposit id you just created.
    """

    payload = request.load_json()
    provider_partner_id = payload.get("provider_partner_id", None)
    receiver_partner_id = payload.get("receiver_partner_id", None)
    if not all([provider_partner_id, receiver_partner_id]):
        raise KeyError("Missing `provider_partner_id` or `receiver_partner_id`")

    engine: ConsigneEngine = request.app.ctx.engine
    res = engine.initialize_return(receiver_partner_id, provider_partner_id)
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
    print(res)
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
async def cancel_returned_product(request: Request, deposit_id: int, deposit_line_id: int) -> HTTPResponse:
    """Cancel a the deposit_line of a returned product.
    the `deposit_id` & `deposit_line_id` path argument combinaison must be valid.
    """

    engine: ConsigneEngine = request.app.ctx.engine
    res = engine.cancel_deposit_line(deposit_id, deposit_line_id)
    return json({"status": 200, "reasons": "OK", "data": {}})

@consigneBp.route("/deposit/<deposit_id:int>/ticket", methods=["GET"])
async def get_ticket(request: Request, deposit_id: int) -> HTTPResponse:
    """Request to generate a ticket for a given deposit."""
    engine: ConsigneEngine = request.app.ctx.engine
    res = engine.generate_ticket(deposit_id)
    return json({"status": 200, "reasons": "OK", "data": {}})


@consigneBp.route("/deposit/<deposit_id:int>/close", methods=["GET"])
async def close_deposit(request: Request, deposit_id: int) -> HTTPResponse:
    engine: ConsigneEngine = request.app.ctx.engine
    res = engine.close_deposit(deposit_id)
    return json({"status": 200, "reasons": "OK", "data": {}})

@consigneBp.route("/search-user", methods=["POST"])
async def search_user(request: Request) -> HTTPResponse:
    """
    POST {'input': int|str}
    return (list[tuple(int, str)]): list of user_code, user_name of X partially matching given output
    """
    payload = request.load_json()
    inp = payload.get("input", None)

    engine: ConsigneEngine = request.app.ctx.engine
    res = engine.search_user(inp)
    return json({"status": 200, "reasons": "OK", "data": {"matches": res}})

@consigneBp.route("/get-shifts-users", methods=["GET"])
async def get_shifts_users(request: Request) -> HTTPResponse:
    engine: ConsigneEngine = request.app.ctx.engine
    users = engine.get_shifts_users()
    return json({"status": 200, "reasons": "OK", "data": {"users": users}})
