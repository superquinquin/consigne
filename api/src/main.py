from __future__ import annotations


import os
from sanic import Sanic
from sanic.log import LOGGING_CONFIG_DEFAULTS


from pathlib import Path

from typing import Any


from src.parsers import get_config
from src.routes import consigneBp
from src.middlewares import error_handler, go_fast, log_exit

from src.odoo import OdooConnector
from src.database import ConsigneDatabase
from src.engine import ConsigneEngine


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
    def initialize_from_configs(
        cls,
        sanic: dict[str, Any],
        odoo: dict[str, Any],
        database: dict[str, Any],
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

        connector = OdooConnector(**odoo)
        consigne_database = ConsigneDatabase(**database)
        engine = ConsigneEngine(connector, consigne_database)
        app.ctx.engine = engine
        consigne = cls(app, engine, env)
        return consigne.app


    @classmethod
    def create_app(cls, path: StrOrPath|None=None) -> Sanic:
        """config path either defined as env var or as argument"""
        env_path = os.environ.get("CONFIG_FILEPATH", None)
        if not any([path, env_path]):
            raise ValueError("You must pass your configuration file path as an argument or as Environment Variable: `CONFIG_FILEPATH`.")
        if path is None:
            path = env_path
        return cls.initialize_from_configs(**get_config(path))

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
    
if __name__ == "__main__":
    Consigne.create_app("configs.yaml")