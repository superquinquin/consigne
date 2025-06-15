import os
import asyncio
from sanic import Sanic
import multiprocessing
import logging
import time

from src.engine import ConsigneEngine, TaskConfigs
from src.odoo import OdooConnector
from src.database import ConsigneDatabase
from src.ticket import ConsignePrinter, UsbSettings, NetworkSettings

tasks_logger = logging.getLogger("tasks")

async def start_redeem_analizer(app: Sanic):
    engine: ConsigneEngine = app.ctx.engine
    settings = engine.tasks.get("analyzer", None)
    if settings is None or settings.pooling is False:
        return
    
    if app.shared_ctx.analyzer.qsize() == 0:
        app.shared_ctx.analyzer.put(1)
        app.add_task(engine.ticket_emissions_analyzer)
    else:
        state = app.shared_ctx.analyzer.get()
        
async def start_barcode_tracking(app: Sanic):
    engine: ConsigneEngine = app.ctx.engine
    
    settings = engine.tasks.get("tracking", None)
    if settings is None or settings.pooling is False:
        return

    if app.shared_ctx.tracker.qsize() == 0:
        app.shared_ctx.tracker.put(1)
        app.add_task(engine.bases_tracker_runner)
    else:
        state = app.shared_ctx.tracker.get()

async def initialize_barcode_bases(app:Sanic):
    engine: ConsigneEngine = app.ctx.engine
    
    if app.shared_ctx.base_init.qsize() == 0:
        app.shared_ctx.base_init.put(1)
        app.add_task(engine.bases_tracker())
    else:
        state = app.shared_ctx.base_init.get()

async def thread_state_manager(app: Sanic):
    app.shared_ctx.analyzer = multiprocessing.Queue()
    app.shared_ctx.base_init = multiprocessing.Queue()
    app.shared_ctx.tracker = multiprocessing.Queue()
