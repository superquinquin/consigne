from __future__ import annotations


import os
from sanic import Sanic
from sanic.log import LOGGING_CONFIG_DEFAULTS
from pymemcache.client.retrying import RetryingClient
from pymemcache.exceptions import MemcacheUnexpectedCloseError


from pathlib import Path

from typing import Any, Literal


from src.loaders import ConfigLoader
from src.routes import consigneBp
from src.middlewares import error_handler, go_fast, log_exit
from src.listeners import start_redeem_analizer, start_barcode_tracking, initialize_barcode_bases, thread_state_manager

from src.odoo import OdooConnector
from src.database import ConsigneDatabase
from src.ticket import ConsignePrinter, UsbSettings, NetworkSettings
from src.cache import ConsigneCache
from src.engine import ConsigneEngine, TaskConfigs


StrOrPath = str|Path

class Consigne:
    """Sanic Consigne app factory"""
    env: str = "development"
    app: Sanic
    engine: ConsigneEngine
    
    def __init__(self, app: Sanic, engine: ConsigneEngine, env: str="development"):
        self.env = env
        self.app = app
        self.engine = engine
        self.print_banner()

    @classmethod
    async def initialize_from_configs(
        cls,
        sanic: dict[str, Any],
        odoo: dict[str, Any],
        database: dict[str, Any],
        printer: dict[str, Any],
        tasks: dict[str, Any] | None = None, 
        caching: dict[str, Any] | None = None,
        logging: dict[str, Any] | None = None,
        options: dict[str, Any] | None = None,
        env: str= "development",
    ) -> Sanic:
        
        app = Sanic("consigne", log_config=cls.setup_logging_configs(logging))
        static = sanic.get("static", None)
        if static is None:
            raise KeyError("Missing `static` field in sanic configs.")
        app.static('/static', static)
        app.config.update({"ENV": env})
        app.config.update({k.upper():v for k,v in sanic.get("app", {}).items()})
        if options is not None:
            app.config.update({k.upper():v for k,v in options.items()})

        app.blueprint(consigneBp)
        app.on_request(go_fast, priority=100)
        app.on_response(log_exit, priority=100)
        app.error_handler.add(Exception, error_handler)

        erp = odoo.get("erp", None)
        if erp is None:
            raise KeyError("Missing configuration for odoo erp.")

        tasks_settings = cls.parse_tasks_settings(tasks)
        
        if caching:
            caching = cls.reformat_caching_configs(caching)
            base_cache = ConsigneCache(**caching)
            cache = RetryingClient(
                base_cache,
                attempts=3,
                retry_delay=0.01,
                retry_for=[MemcacheUnexpectedCloseError],
            )
        else:
            cache = None
        connector = OdooConnector(**erp)
        consigne_database = ConsigneDatabase(**database)
        consigne_printer = ConsignePrinter.from_configs(**printer)
        engine = ConsigneEngine(connector, consigne_database, consigne_printer, cache, tasks_settings)

        app.ctx.engine = engine
        consigne = cls(app, engine, env)

        app.register_listener(thread_state_manager, "main_process_start")
        app.register_listener(initialize_barcode_bases, "before_server_start")
        app.register_listener(start_barcode_tracking, "before_server_start")
        app.register_listener(start_redeem_analizer, "before_server_start")
        return consigne.app

    @classmethod
    async def create_app(cls, path: StrOrPath|None=None) -> Sanic:
        """config path either defined as env var or as argument"""
        env_path = os.environ.get("CONFIG_FILEPATH", None)
        if not any([path, env_path]):
            raise ValueError("You must pass your configuration file path as an argument or as Environment Variable: `CONFIG_FILEPATH`.")
        if path is None:
            path = env_path
        configs = ConfigLoader().load(path)
        return await cls.initialize_from_configs(**configs)

    def print_banner(self) -> None:
        version = Path("./src/VERSION").read_text()
        banner = Path("./src/banner").read_text()
        banner = banner[:-8] + f"v{version}"
        print(banner)
        print(f"Booting env: {self.env}")

    @staticmethod
    def setup_logging_configs(logging: dict[str, Any] | None) -> dict[str, Any]:
        if logging is None:
            return LOGGING_CONFIG_DEFAULTS
        logging["loggers"].update(LOGGING_CONFIG_DEFAULTS["loggers"])
        logging["handlers"].update(LOGGING_CONFIG_DEFAULTS["handlers"])
        logging["formatters"].update(LOGGING_CONFIG_DEFAULTS["formatters"])
        return logging

    @staticmethod
    def parse_tasks_settings(tasks: dict[str, Any]|None=None) -> dict[str, TaskConfigs]:
        if tasks is None:
            return {}
        return {k:TaskConfigs(**v) for k,v in tasks.items()}
    
    @staticmethod
    def reformat_caching_configs(caching: dict[str, Any]) -> dict[str, Any]:
        caching.update({"servers": [(s["host"], s["port"]) for s in caching.get("servers")]})
        return caching


if __name__ == "__main__":
    Consigne.create_app("configs.yaml")