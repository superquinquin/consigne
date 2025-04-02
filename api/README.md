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

### Odoo
Consigne needs to have few setup to be made on your Odoo.

A simple command line can all those setup task for you, as long as you configurate the setup process:
```bash
Usage: consigne setup [OPTIONS]

Options:
  -c, --config TEXT  your config file path
  --help             Show this message and exit.

```

In your configuration file must contain the `app.odoo.taxonomy` section:
```yaml
app:
  ...
  odoo:
    taxonomy:

      products: # configurations for consgine product generation
        # this configuration aim to generate 10 consigne Product called `Consigne`  with randomized and unique barcodes.
        # !important to be builded using this tool as the created barcodes are tracked by Consigne app!

        variation_number: 10 # number of consigne product you want in circulation 
        in_place: True # When true, check the number of product already in use. block the process to create to exceed variation_number value
        template: # template define the name all variation will have and the barcode rule they follow.
          name: Consigne
          rule: 999....{NNNDD}

      returns: # configuration for the consigne returns generation
        ## contains a list of all returns you want to create. You can simply describe the name and the value of each returns.
        - name: Pajot
          value: 0.25

      returnables: # configuration for updating returnable products and embedding the correct product return into them.
        # Make sure to provide the barcode of the returnable product, and the name of the product return 
        - barcode: 5411087001029 # barcode of the returnable product 
          returnable: True
          returned: Pajot # name of the returns product possibly from returns
    
    ...
```

#### Taxonomies
Some categories must create to hold your Consigne Products (Products that are going to be scanned to get the discount) & the Consigne returns which are the the return values that must be embedded into your returnable products.

#### Consigne Return Products
The Creation of Your consigne return products. those products can be reduced to a Consigne Name and a consigne value, e.g: name: Botlle 33cl, return_value: 0.20. 

A return product is embedable on returnable items. When printing a consigne ticket, the details are grouped by return product types and the total values are summed.

#### Consigne Products
The Creation of Your Consigne Products. A consigne product is a product available in your odoo POS. When printing a consigne ticket, the barcode used is the one from your consigne product. Your consigne Products allow the Consigne system to be used in the Odoo POS.

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