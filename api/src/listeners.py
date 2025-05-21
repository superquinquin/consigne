from sanic import Sanic

from src.engine import ConsigneEngine

async def start_redeem_analizer(app: Sanic):
    engine: ConsigneEngine = app.ctx.engine
    settings = engine.tasks.get("analyzer", None)
    if settings is None or settings.pooling is False:
        return

    app.add_task(engine.ticket_emissions_analyze())

async def start_barcode_tracking(app: Sanic):
    engine: ConsigneEngine = app.ctx.engine
    
    settings = engine.tasks.get("tracking", None)
    if settings is None or settings.pooling is False:
        return

    app.add_task(engine.bases_tracker_runner())

async def initialize_barcode_bases(app:Sanic):
    engine: ConsigneEngine = app.ctx.engine
    app.add_task(engine.bases_tracker())