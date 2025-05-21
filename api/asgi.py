import asyncio
from src.main import Consigne

app = asyncio.run(Consigne.create_app("configs.yaml"))
