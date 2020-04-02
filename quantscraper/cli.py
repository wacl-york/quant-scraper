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
import configparser
from datetime import date, timedelta, datetime, time
import requests as re
import quantaq
import traceback

from quantscraper.utils import LoginError
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
        except LoginError:
            logging.error("Cannot establish connection to {}.".format(man_class.name))
            logging.error(traceback.format_exc())
            continue

        logging.info("Scraping all devices.")
        # TODO Scrape function just iterates through all devices and calls
        # .scrape_device().
        # Should this be instead be run from here, rather than Manufacturer?
        # Particularly since it handles error logging
        manufacturer.scrape()

        # TODO Whose responsibility is it to generate filename? CLI script or
        # manufacturer? Currently filename is built in
        # Manufacturer.save_raw_data from these input values
        if cfg.getboolean("Main", "save_raw_data"):
            logging.info("Saving raw data to file.")
            manufacturer.save_raw_data(
                cfg.get("Main", "folder_raw_data"),
                cfg.get("Main", "start_time"),
                cfg.get("Main", "end_time"),
            )

        # TODO Ditto above issue about whether the iterating through each device
        # should be run here rather than from Manufacturer, so that only have 1
        # place that is logging.
        logging.info("Processing raw data into validated cleaned data.")
        manufacturer.process()

        if cfg.getboolean("Main", "save_clean_data"):
            logging.info("Saving clean CSV data to file.")
            manufacturer.save_clean_data(
                cfg.get("Main", "folder_clean_data"),
                cfg.get("Main", "start_time"),
                cfg.get("Main", "end_time"),
            )


if __name__ == "__main__":
    main()
