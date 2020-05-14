![Python application](https://github.com/wacl-york/QUANTscraper/workflows/Python%20application/badge.svg?branch=master)
![Test coverage](https://webfiles.york.ac.uk/WACL/QUANT/QUANTscraper/resources/coverage.svg)

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

Once a suitable version of Python has been made available, the `quantscraper` package can be installed from GitHub by using the following command.

`pip install git+https://github.com/wacl-york/QUANTscraper.git@master`

# Running the scraper

The installation processes places an executable called `quant_scrape` in the user's `PATH` and is run with the following command.

`quant_scrape`

By default, the scraper will run for all available instruments over the 24 hour period from midnight of the previous day to 1 second before midnight of the current day.
A summary of the scraping is output to `stdout`, while a log will be displayed on `stderr`.
Command line arguments allow for the specification of the instruments to scrape and the timeframe, in addition to uploading the resultant data to Google Drive and saving an HTML summary table.

Run `quant_scrape --help` to see the available options.

## Scrapping configuration

This requires a configuration file called `config.ini` to be present in the directory where the executable is called from.
This file provides parameters for the scraping; `example.ini` shows the required format.

## Manufacturer and Device specification

In addition, it requires the presence of a file called `devices.json` in the working directory.
This file maps the relationship between the manufacturers and the devices in the study.
Each entry in the `manufacturers` list reflects an air quality instrumentation company included in the study, with the `properties` object providing keyword-value properties that must be completed before running the program.
The `fields` list defines the measurands recorded by devices from this company, represented by an object containing a human readable label (`id`), an ID used to refer to this measurand by the company in the downloaded data (`webid`), and a `scale` parameter that is multiplied by the raw value.
The `devices` list holds a record of the physical instruments installed from this company, represented by an object containing a human readable label (`id`), an ID used to refer to this device by the company on their system (`webid`), and a description of where the device is installed (`location`).

The example file `example_devices.json` shows the required layout.

# Running the pre-processing

In addition to the CLI scraping program there is a pre-processing script, which takes the cleaned and validated data as stored by the `quant_scrape` command, and organises the data into a format suitable for analysis.

In particular, it converts the data from being saved in long format with 1 file per device, into wide format with 1 file per manufacturer.
It also resamples the time-series so that the air quality data from all manufacturers is saved at the same sampling rate.

The program is run using the `quant_preprocess` command that should be added to the `PATH` as part of the installation. 

As with the scraping program, it requires the presence of `devices.json` in the working directory to define the manufacturers and devices included in the study.
It also requires its own separate configuration file to be present in the working directory: `preprocessing.ini`.
An example is provided by `example_preprocessing.ini`.

By default the program pre-processes the previous day's cleaned data for all available instruments, although this behaviour can be configured by setting a YYYY-mm-dd formatted date to the `--date` argument and specifying the devices with the `--devices` flag.
Furthermore, the resultant processed data can be uploaded to Google Drive by setting the `--upload` flag.
Run `quant_preprocess --help` to see the available options.

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
