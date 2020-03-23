# QUANTscraper
Scrapes data from the websites of air quality instrumentation system manufacturers for the QUANT project

# Installation

There are a number of dependencies that need to be installed prior to running the scraper.
These can either be installed automatically through the use of the `conda` environment manager, or manually setup. 
I would recommend the former, although it hasn't been tested on a new machine as of yet.

## Conda environment

Conda can be installed from their website: [https://docs.conda.io/en/latest/](https://docs.conda.io/en/latest/). 
If it is only going to be used for this project, I would recommend the [`miniconda` version](https://docs.conda.io/en/latest/miniconda.html), as it is more minimalist and just contains libraries required to run Python.

Firstly clone this repository:

`git clone https://github.com/wacl-york/QUANTscraper.git`

Then navigate into the local folder:

`cd QUANTscraper`

Once `conda` is installed, run the following command, which will create a conda environment called `QUANTscraper` with all the dependencies already installed (*NB: this hasn't been tested yet*).

`conda env create -f environment.yml`

To run Python inside this environment, simply use the following command:

`conda activate QUANTscraper`

## Manual

Alternatively, the dependencies can be installed manually.

The scraper runs on Python 3.7 or higher, and requires a number of packages to be installed from `pip`:

  - `pandas`
  - `numpy`
  - `requests`

In addition to these packages, there is a [Python wrapper](https://github.com/quant-aq/py-quantaq) for accessing QuantAQ's API, which can be installed from GitHub using the following command:

`pip install git+https://github.com/quant-aq/py-quantaq.git`

Finally, the [`Black` formatter](https://github.com/psf/black) is used in development as a pre-commit hook to ensure consistent formatting across source files. 
It can also be installed through `pip`.

# Running the scraper

The scraper can be run through the `main.py` script.
This takes one obligatory argument: the location of an INI file containing configuration parameters for the scraping, including:

  - website credentials
  - timeframe to collect data from
  - parameters for each website
  - where to save output data to

An example configuration file is provided: `example.ini`, which shows the format of the various options.

The scraper is run by issuing the following command:

`python main.py example.ini`

A log will be displayed on `stdout`, which can be redirected to a file for long-term logging.

