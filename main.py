#!/usr/bin/env python3
"""
    main.py
    ~~~~~~~

    Main scraper script that collects data from each of the four manufacturers.
    By default it obtains all data from midnight to the following midnight of
    the previous day.  This behaviour can be changed in the config.ini file, which is also where credentials are stored.
"""

import pickle
import os
import sys
import argparse
import configparser
from datetime import date, timedelta, datetime, time
import requests as re
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
    print(args)
    print(config)

    # Get yesterday's date. Assume that will be scraping from yesterday
    # according to timezone of the device where this script is run from, i.e. no
    # timezone issues. Otherwise date to collect results from can be set in
    # the config file.
    # Will keep this as date, rather than datetime object, as each manufacturer
    # will want to parse datetime accordingly, i.e. some use inclusive and some
    # exclusive dates
    yesterday = date.today() - timedelta(days=1)
    try:
        start_datetime = config.get("Main", "start_time")
    except configparser.NoOptionError:
        config["Main"]["start_time"] = datetime.combine(yesterday, time.min).isoformat()
    try:
        end_datetime = config.get("Main", "end_time")
    except configparser.NoOptionError:
        config["Main"]["end_time"] = datetime.combine(yesterday, time.max).isoformat()

    # Load all manufacturers
    # manufacturers = [Aeroqual, AQMesh, Zephyr, MyQuantAQ]
    # for manufacturer in manufacturers:
    #    _instance = manufacturer(config)
    #    _instance.scrape()
    #    print(_instance.scrape())

    # TODO implement Manufacturer.clean() method
    # aeroqual = Aeroqual(config)

    # Save raw data locally for testing process data method
    # aeroqual.scrape()
    # with open('aeroqual_raw.pickle', 'wb') as f:
    #    pickle.dump(aeroqual._raw_data, f)

    # with open('aeroqual_raw.pickle', 'rb') as f:
    #    aeroqual._raw_data = pickle.load(f)
    # aeroqual.process_data()

    # aqmesh = AQMesh(config)

    # aqmesh.scrape()
    # with open('aqmesh_raw.pickle', 'wb') as f:
    #    pickle.dump(aqmesh._raw_data, f)

    # with open('aqmesh_raw.pickle', 'rb') as f:
    #    aqmesh._raw_data = pickle.load(f)
    # aqmesh.process_data()

    zephyr = Zephyr(config)

    # zephyr.scrape()
    # with open('zephyr_raw.pickle', 'wb') as f:
    #    pickle.dump(zephyr._raw_data, f)

    with open("zephyr_raw.pickle", "rb") as f:
        zephyr._raw_data = pickle.load(f)
    zephyr.process_data()

    # myquantaq = MyQuantAQ(config)
    # myquantaq.scrape()
    # with open('myquantaq_raw.pickle', 'wb') as f:
    #    pickle.dump(myquantaq._raw_data, f)

    # with open('myquantaq_raw.pickle', 'rb') as f:
    #    myquantaq._raw_data = pickle.load(f)
    # myquantaq.process_data()


if __name__ == "__main__":
    main()
