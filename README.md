![Python application](https://github.com/wacl-york/QUANTscraper/workflows/Python%20application/badge.svg?branch=master)
![Test coverage](resources/coverage.svg)

# QUANTscraper

Scrapes data from the websites of air quality instrumentation system manufacturers for the QUANT project.

# Installation

## Python 3.7

A recent installation of Python (>= 3.7) needs to be available.
This can be installed manually, or through the `conda` environment manager.

Conda can be installed from their website: [https://docs.conda.io/en/latest/](https://docs.conda.io/en/latest/). 
If it is only going to be used for this project, I would recommend the [`miniconda` version](https://docs.conda.io/en/latest/miniconda.html), as it is more minimalist and just contains libraries required to run Python.

A `conda` environment can be created with Python 3.7 through the following command.

`conda create --name <ENVNAME> python=3.7`

And can be used through

`conda activate <ENVNAME>`

# Installing QUANTscraper

Once a suitable version of Python has been made available, the `quantscraper` package can be installed from GitHub by using the following command (NB: this URL will be changed to use a stable release tag, or master branch rather than current development branch).

`pip install git+https://github.com/wacl-york/QUANTscraper.git@initial-release`

# Running the scraper

The installation processes places an executable called `quant_scrape` in the user's `PATH` and is run with the following command.

`quant_scrape example.ini`

This takes one obligatory argument: the location of an INI file containing configuration parameters for the scraping, including:

  - website credentials
  - timeframe to collect data from
  - parameters for each website
  - where to save output data to

The example configuration file (`example.ini`) shows the required format.

A log will be displayed on `stdout`, which can be redirected to a file for long-term logging.

# Running the pre-processing

In addition to the CLI scraping program there is a pre-processing script, which takes the cleaned and validated data as stored by the `quant_scrape` command, and organises the data into a format suitable for analysis.

In particular, it converts the data from being saved in long format with 1 file per device, into wide format with 1 file per manufacturer.
It also resamples the time-series so that the air quality data from all manufacturers is saved at the same sampling rate.

The program is run using the `quant_preprocess` command that should be added to the `PATH` as part of the installation and accepts a JSON configuration file. 
The JSON file specifies which manufacturers and devices should be scraped, along with other settings similar to the `.ini` file used by the scraper.
An example file is provided in this repo for reference.

`quant_preprocess example_preprocessing.json`

By default the program pre-processes the previous day's cleaned data, although this behaviour can be configured by specifying the date at the top level of the JSON file, i.e. `'date': '2020-03-17'`.
If provided, it must be in YYYY-mm-dd format.

# Contributing to development

To contribute to the development of `quantscraper`, firstly clone this repository:

`git clone https://github.com/wacl-york/QUANTscraper.git`

## conda 

The development environment can be replicated by creating a new `conda` environment from the supplied configuration file.

`conda env create -f environment.yml`

This will create a `conda` environment called `QUANTscraper` and install all the dependencies.
If it fails to install all dependencies then it should create an empty environment called `QUANTscraper`, which can be activated as below with the remaining dependencies installed as per the `Manual` instructions below.

Use this environment by entering

`conda activate QUANTscraper`

## Manual

Optionally, the dependencies can be installed manually.
The scraper runs on Python 3.7 or higher, and requires a number of packages to be installed from `pip`:

  - `pandas`
  - `numpy`
  - `requests`
  - `bs4`

In addition to these packages, there is a [Python wrapper](https://github.com/quant-aq/py-quantaq) for accessing QuantAQ's API, which can be installed from GitHub using the following command:

`pip install git+https://github.com/quant-aq/py-quantaq.git`

Finally, the [`Black` formatter](https://github.com/psf/black) is used in development as a pre-commit hook to ensure consistent formatting across source files. 
It can also be installed through `pip`.

## Testing

All unit tests can be run using the following command:

`coverage run -m unittest discover -s tests -b`

Test coverage can be viewed by running `coverage report` afterwards.

## Running the program during development

To run the program scripts while developing, install it locally in editable mode with:

`pip install -e .`

This will add the appropriate package imports to your `PYTHONPATH` and will update them when needed.

You can then run the main scripts with `python quantscraper/cli.py` or `python quantscraper/daily_preprocessing.py`.
