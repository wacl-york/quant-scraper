#!/usr/bin/env python3
"""
    cli.py
    ~~~~~~

    Main scraper script that collects data from each of the four manufacturers.
    By default it obtains all data from midnight to the following midnight of
    the previous day.  This behaviour can be changed in the config.ini file, which is also where credentials are stored.
"""

import logging
import argparse
import os
import configparser
from datetime import date, timedelta, datetime, time
import requests as re
import quantaq
import traceback

import quantscraper.utils as utils
from quantscraper.manufacturers.Aeroqual import Aeroqual
from quantscraper.manufacturers.AQMesh import AQMesh
from quantscraper.manufacturers.Zephyr import Zephyr
from quantscraper.manufacturers.MyQuantAQ import MyQuantAQ


def parse_args():
    """
    Parses CLI arguments to the script.

    Args:
        - None

    Returns:
        An argparse.Namespace object.
    """
    parser = argparse.ArgumentParser(description="QUANT scraper")
    parser.add_argument(
        "configfilepath", metavar="FILE", help="Location of INI configuration file"
    )
    args = parser.parse_args()
    return args


def setup_scraping_timeframe(cfg):
    """
    Sets up the scraping timeframe in the configuration.

    By default, this script attempts to scrape from midnight of the day prior to
    the script being executed, to 1 second before the following midnight.
    I.e. if the script is run at 2020-01-08 15:36:00, then the default scraping
    window is between 2020-01-07 00:00:00 and 2020-01-07 23:59:59.

    If the Main.start_time and Main.end_time configuration parameters in the
    INI file are supplied then this default behaviour is overruled.

    Args:
        cfg: configparser Namespace object. Stores the contents of the INI file.

    Returns:
        None. Updates cfg by reference as a side-effect.
    """
    yesterday = date.today() - timedelta(days=1)
    try:
        cfg.get("Main", "start_time")
    except configparser.NoOptionError:
        cfg["Main"]["start_time"] = datetime.combine(yesterday, time.min).isoformat()
    try:
        cfg.get("Main", "end_time")
    except configparser.NoOptionError:
        cfg["Main"]["end_time"] = datetime.combine(yesterday, time.max).isoformat()


def setup_loggers(logfn):
    """
    Configures loggers.

    By default, the error log is printed to standard out,
    although it can be saved to file in addition.

    Args:
        logfn: File to save log to. If None then doesn't write log to file.

    Returns:
        None. the logger is accessed by the global module `logging`.
    """
    rootLogger = logging.getLogger()
    rootLogger.setLevel(logging.INFO)
    logFmt = logging.Formatter(
        "%(asctime)-8s:%(levelname)s: %(message)s", datefmt="%Y-%m-%d,%H:%M:%S"
    )
    cliLogger = logging.StreamHandler()
    cliLogger.setFormatter(logFmt)
    rootLogger.addHandler(cliLogger)

    if not logfn is None:
        if os.path.isfile(logfn):
            logging.error(
                ("Log file {} already exists. " "Halting execution.").format(logfn)
            )
            sys.exit()
        fileLogger = logging.FileHandler(logfn)
        fileLogger.setFormatter(logFmt)
        rootLogger.addHandler(fileLogger)


def save_clean_data(manufacturer, folder, start_time, end_time):
    """
    Iterates through all a manufacturer's devices and saves their cleaned data to disk.

    Uses the following template filename:

    <manufacturer_name>_<deviceid>_<start_timeframe>_<end_timeframe>.csv

    Args:
        - manufacturer (Manufacturer): Instance of Manufacturer.
        - folder (str): Directory where files should be saved to.
        - start_time (str): Starting time of scraping window. In same
            string format as INI file uses.
        - end_time (str): End time of scraping window. In same
            string format as INI file uses.

    Returns:
        None. Saves data to disk as CSV files as a side-effect.
    """
    # TODO Change start + end time to just a single date, as this is primary
    # usecase?

    if not os.path.isdir(folder):
        raise utils.DataSavingError(
            "Folder {} doesn't exist, cannot save clean data.".format(folder)
        )

    for devid in manufacturer.device_ids:
        fn = utils.CLEAN_DATA_FN.substitute(
            man=manufacturer.name, device=devid, start=start_time, end=end_time
        )

        data = manufacturer.clean_data[devid]
        if data is None:
            logging.warning(
                "No clean data to save for device {}.".format(devid)
            )
            continue

        full_path = os.path.join(folder, fn)
        logging.info("Saving data to file: {}".format(full_path))
        utils.save_csv_file(full_path, data)

def save_raw_data(manufacturer, folder, start_time, end_time):
    """
    Iterates through all a manufacturer's devices and saves their raw data to disk.

    Uses the following template filename:

    <manufacturer_name>_<deviceid>_<start_timeframe>_<end_timeframe>.json

    Args:
        - manufacturer (Manufacturer): Instance of Manufacturer.
        - folder (str): Directory where files should be saved to.
        - start_time (str): Starting time of scraping window. In same
            string format as INI file uses.
        - end_time (str): End time of scraping window. In same
            string format as INI file uses.

    Returns:
        None. Saves data to disk as CSV files as a side-effect.
    """
    # TODO Change start + end time to just a single date, as this is primary
    # usecase?

    if not os.path.isdir(folder):
        raise utils.DataSavingError(
            "Folder {} doesn't exist, cannot save raw data.".format(folder)
        )

    for devid in manufacturer.device_ids:
        fn = utils.RAW_DATA_FN.substitute(
            man=manufacturer.name, device=devid, start=start_time, end=end_time
        )

        data = manufacturer.raw_data[devid]
        if data is None:
            logging.warning(
                "No raw data to save for device {}.".format(devid)
            )
            continue

        full_path = os.path.join(folder, fn)
        logging.info("Saving data to file: {}".format(full_path))
        utils.save_json_file(full_path, data)


def main():
    """
    Entry point into the script.

    Args:
        - None

    Returns:
        None.
    """
    # Setup logging
    # TODO For now just log to stdout
    setup_loggers(None)

    # Parse config file
    args = parse_args()
    # TODO validate config file's existence and format

    cfg = configparser.ConfigParser()
    cfg.read(args.configfilepath)
    setup_scraping_timeframe(cfg)

    # Load all manufacturers
    manufacturers = [Aeroqual, AQMesh, Zephyr, MyQuantAQ]
    for man_class in manufacturers:
        logging.info("Manufacturer: {}".format(man_class.name))
        manufacturer = man_class(cfg)

        try:
            logging.info("Attempting to connect...")
            manufacturer.connect()
            logging.info("Connection established")
        except utils.LoginError:
            logging.error("Cannot establish connection to {}.".format(man_class.name))
            logging.error(traceback.format_exc())
            continue

        # TODO Scrape function just iterates through all devices and calls
        # .scrape_device().
        # Should this be instead be run from here, rather than Manufacturer?
        # Particularly since it handles error logging
        logging.info("Scraping all devices.")
        manufacturer.scrape()
        # TODO Ditto 
        logging.info("Processing raw data into validated cleaned data.")
        manufacturer.process()

        if cfg.getboolean("Main", "save_raw_data"):
            logging.info("Saving raw data to file.")
            save_raw_data(
                manufacturer,
                cfg.get("Main", "folder_raw_data"),
                cfg.get("Main", "start_time"),
                cfg.get("Main", "end_time"),
            )

        if cfg.getboolean("Main", "save_clean_data"):
            logging.info("Saving clean CSV data to file.")
            save_clean_data(
                manufacturer,
                cfg.get("Main", "folder_clean_data"),
                cfg.get("Main", "start_time"),
                cfg.get("Main", "end_time"),
            )

        # TODO Upload both raw and clean data to Google Drive


if __name__ == "__main__":
    main()
