# Consigne APi
Backend for consigne

## Setup
### database
```bash
cat schema.sql | sqlite3 database.db
```
Or using `boot.sh` systematically check and create if necessary the database before starting the sanic server:
```bash
bash boot.sh
```
### Configurations
Consigne is configurated using a `yaml` file, generally called `configs.yaml`.
this file can either be defined as the `path` argument of the `create_app` method in `asgi.py` 
or it can be set as an environment variable named `CONFIG_FILEPATH`.

For security reasons, part of the configuration values are collected from the environment Variable.
Any values being annoted as follow `${YOUR ENV VARIABLE NAME}` are collected from your environment during the initialisation process.
Thus it is best practice to set all your sensitive data as environment variable and to reference them in your configuration file.

Default configurations put all logs inside a `volume` folder. Before starting the server make sure to create this folder or to change the logging path
```bash
mkdir volume
```

### Dev Setup
Consigne api use [UV](https://docs.astral.sh/uv/) as it's depedencies manager.

```bash
# Installing UV
curl -LsSf https://astral.sh/uv/install.sh | sh
```

on `./api` create and activate the virtual environment for the consigne api.
```bash
# Installing consigne dependencies from uv.lock
uv sync

# activate the virtual env
source .venv/bin/activate
```

to boot consigne api
```bash
# Running the sanic server.
bash boot.sh
```
### Prod Setup
...