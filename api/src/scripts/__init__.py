import click
from src.scripts.set_consigne_products import *

__all__ = ["set_products", "Builder"]

@click.group()
def cli():
    pass

@cli.command()
@click.option("-c", "--config", default="configs.yaml", help="your config file path. Default: `configs.yaml`.")
def setup(config: str) -> None:
    Builder.from_configs(config).run()


if __name__ == "__main__":
    cli()