#!/usr/bin/env python3
"""
    main.py
    ~~~~~~~

    Main scraper script that collects data from each of the four manufacturers.
    By default it obtains all data from midnight to the following midnight of
    the previous day.  This behaviour can be changed in the config.ini file, which is also where credentials are stored.
"""

import sys
import argparse
import configparser
from datetime import date, timedelta, datetime, time
import quantaq

from Aeroqual import Aeroqual
from AQMesh import AQMesh
from Zephyr import Zephyr
from MyQuantAQ import MyQuantAQ


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


def main():
    """
    Entry point into the script.

    Args:
        - None

    Returns:
        None.
    """

    # Parse config file
    args = parse_args()
    # TODO validate config file's existence and format

    config = configparser.ConfigParser()
    config.read(args.configfilepath)
    setup_scraping_timeframe(config)

    # Load all manufacturers
    manufacturers = [Aeroqual, AQMesh, Zephyr, MyQuantAQ]
    for man_class in manufacturers:
        manufacturer = man_class(config)
        manufacturer.scrape()
        manufacturer.process_data()
        # manufacturer.save_data()


if __name__ == "__main__":
    main()
