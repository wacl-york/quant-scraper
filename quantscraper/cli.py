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
import sys
import configparser
from datetime import date, timedelta, datetime, time
import traceback

import quantscraper.utils as utils
from quantscraper.manufacturers.Aeroqual import Aeroqual
from quantscraper.manufacturers.AQMesh import AQMesh
from quantscraper.manufacturers.Zephyr import Zephyr
from quantscraper.manufacturers.MyQuantAQ import MyQuantAQ


def setup_loggers(logfn=None):
    """
    Configures loggers.

    By default, the error log is printed to standard out,
    although it can be saved to file in addition.

    Args:
        logfn (str): File to save log to. If None then doesn't write log to file.

    Returns:
        None. the logger is accessed by the global module `logging`.
    """
    rootLogger = logging.getLogger("cli")
    rootLogger.setLevel(logging.INFO)
    logFmt = logging.Formatter(
        "%(asctime)-8s:%(levelname)s: %(message)s", datefmt="%Y-%m-%d,%H:%M:%S"
    )
    cliLogger = logging.StreamHandler()
    cliLogger.setFormatter(logFmt)
    rootLogger.addHandler(cliLogger)

    if not logfn is None:
        if os.path.isfile(logfn):
            raise utils.SetupError(
                ("Log file {} already exists. " "Halting execution.").format(logfn)
            )
        fileLogger = logging.FileHandler(logfn)
        fileLogger.setFormatter(logFmt)
        rootLogger.addHandler(fileLogger)


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


def setup_config(fn):
    """
    Loads configuration parameters from file into memory.

    Args:
        fn (str): Filepath of the .INI file.

    Returns:
        A ConfigParser() instance.
    """
    cfg = configparser.ConfigParser()
    cfg.read(fn)

    if len(cfg.sections()) == 0:
        raise utils.SetupError("No sections found in '{}'".format(fn))

    return cfg


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
    docs_url = "https://docs.python.org/3/library/datetime.html#datetime.datetime.fromisoformat"
    error_msg = (
        "Unknown ISO 8601 format '{input}'. Available formats are described at {url}"
    )

    yesterday = date.today() - timedelta(days=1)
    try:
        cfg.get("Main", "start_time")
    except configparser.NoOptionError:
        cfg["Main"]["start_time"] = datetime.combine(yesterday, time.min).isoformat()
    try:
        cfg.get("Main", "end_time")
    except configparser.NoOptionError:
        cfg["Main"]["end_time"] = datetime.combine(yesterday, time.max).isoformat()

    # Confirm that both dates are valid
    try:
        start_dt = datetime.fromisoformat(cfg.get("Main", "start_time"))
    except ValueError:
        raise utils.TimeError(
            error_msg.format(input=cfg.get("Main", "start_time"), url=docs_url)
        )
    try:
        end_dt = datetime.fromisoformat(cfg.get("Main", "end_time"))
    except ValueError:
        raise utils.TimeError(
            error_msg.format(input=cfg.get("Main", "end_time"), url=docs_url)
        )

    if start_dt >= end_dt:
        raise utils.TimeError(
            "Start date must be earlier than end date. ({} - {})".format(
                cfg.get("Main", "start_time"), cfg.get("Main", "end_time")
            )
        )


def scrape(manufacturer):
    """
    TODO
    """
    for webid, devid in zip(manufacturer.device_web_ids, manufacturer.device_ids):
        try:
            logging.info("Attempting to scrape data for device {}...".format(devid))
            manufacturer.raw_data[devid] = manufacturer.scrape_device(webid)
            logging.info("Scrape successful.")
        except utils.DataDownloadError as ex:
            logging.error("Unable to download data for device {}.".format(devid))
            logging.error(traceback.format_exc())
            manufacturer.raw_data[devid] = None


def process(manufacturer):
    """
    TODO
    """
    for devid in manufacturer.device_ids:

        logging.info("Cleaning data from device {}...".format(devid))
        if manufacturer.raw_data[devid] is None:
            logging.warning("No available raw data")
            manufacturer.clean_data[devid] = None
            continue

        try:
            logging.info("Attempting to parse data into CSV...")
            manufacturer.clean_data[devid] = manufacturer.parse_to_csv(
                manufacturer.raw_data[devid]
            )
            logging.info(
                "Parse successful. {} samples have been recorded.".format(
                    len(manufacturer.clean_data[devid])
                )
            )
        except utils.DataParseError as ex:
            logging.error("Unable to parse data into CSV for device {}.".format(devid))
            logging.error(traceback.format_exc())
            # TODO Should have a separate attribute for clean and CSV data
            manufacturer.clean_data[devid] = None
            continue

        logging.info("Running validation...")
        try:
            manufacturer.clean_data[devid] = manufacturer.validate_data(
                manufacturer.clean_data[devid]
            )
            # TODO is this message accurate?
            logging.info(
                "Validation successful. There are {} samples with no errors.".format(
                    len(manufacturer.clean_data[devid])
                )
            )
        except utils.ValidateDataError:
            logging.error("Something went wrong during data validation.")
            manufacturer.clean_data[devid] = None


def save_data(manufacturer, folder, start_time, end_time, type):
    """
    Iterates through all a manufacturer's devices and saves their raw or clean data to disk.

    Uses the following template filename:

    <manufacturer_name>_<deviceid>_<start_timeframe>_<end_timeframe>.<json/csv>

    Args:
        - manufacturer (Manufacturer): Instance of Manufacturer.
        - folder (str): Directory where files should be saved to.
        - start_time (str): Starting time of scraping window. In same
            string format as INI file uses.
        - end_time (str): End time of scraping window. In same
            string format as INI file uses.
        - type (str): Either 'raw' or 'clean' to indicate which data is being
            saved.

    Returns:
        List of filenames that were successfully saved.
    """
    # TODO Change start + end time to just a single date, as this is primary
    # usecase?
    fns = []

    if type == "clean":
        fn_template = utils.CLEAN_DATA_FN
        manufacturer_data = manufacturer.clean_data
        saving_function = utils.save_csv_file
    elif type == "raw":
        fn_template = utils.RAW_DATA_FN
        manufacturer_data = manufacturer.raw_data
        saving_function = utils.save_json_file
    else:
        raise utils.DataSavingError("Unknown data type '{}'.".format(type))

    if not os.path.isdir(folder):
        raise utils.DataSavingError(
            "Folder {} doesn't exist, cannot save raw data.".format(folder)
        )

    for devid in manufacturer.device_ids:
        fn = fn_template.substitute(
            man=manufacturer.name, device=devid, start=start_time, end=end_time
        )

        data = manufacturer_data[devid]
        if data is None:
            logging.warning("No raw data to save for device {}.".format(devid))
            continue

        full_path = os.path.join(folder, fn)
        logging.info("Saving data to file: {}".format(full_path))
        saving_function(data, full_path)
        fns.append(full_path)
    return fns


def upload_data_googledrive(service, fns, folder_id, mime_type):
    """
    Uploads a number of files of the same type to a single GoogleDrive folder.

    Args:
        service (googleapiclient.discovery.Resource): Handle to GoogleAPI.
        fns (list): A list of full filepaths to the files to be uploaded.
        folder_id (str): The GoogleDrive ID of the target folder.
        mime_type (str): The MIME type of the files.

    Returns:
        None, uploads files as a side-effect.
    """
    if fns is None:
        logging.error(
            "No filenames found. Cannot upload files to Google Drive without saving them locally first. Ensure that option Main.save_<raw/clean>_data is 'true'."
        )
        return

    for fn in fns:
        try:
            logging.info("Uploading file {} to folder {}...".format(fn, folder_id))
            utils.upload_file_google_drive(service, fn, folder_id, mime_type)
            logging.info("Upload successful.")
        except utils.DataUploadError:
            logging.error("Error in upload")
            logging.error(traceback.format_exc())
            continue


def main():
    """
    Entry point into the script.

    Args:
        - None

    Returns:
        None.
    """
    # Setup logging, which for now just logs to stdout
    try:
        setup_loggers()
    except utils.SetupError:
        logging.error("Error in setting up loggers.")
        logging.error(traceback.format_exc())
        logging.error("Terminating program")
        sys.exit()

    # Parse args and config file
    args = parse_args()
    try:
        cfg = setup_config(args.configfilepath)
    except utils.SetupError:
        logging.error("Error in setting up configuration properties")
        logging.error(traceback.format_exc())
        logging.error("Terminating program")
        sys.exit()

    setup_scraping_timeframe(cfg)

    # Load all manufacturers
    manufacturers = [Aeroqual, AQMesh, Zephyr, MyQuantAQ]
    for man_class in manufacturers:
        logging.info("Manufacturer: {}".format(man_class.name))
        try:
            manufacturer = man_class(cfg)
        except utils.DataParseError:
            logging.error("Error instantiating Manufacturer instance.")
            logging.error(traceback.format_exc())
            continue

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
            raw_fns = save_data(
                manufacturer,
                cfg.get("Main", "local_folder_raw_data"),
                cfg.get("Main", "start_time"),
                cfg.get("Main", "end_time"),
                "raw",
            )

        if cfg.getboolean("Main", "save_clean_data"):
            logging.info("Saving clean CSV data to file.")
            clean_fns = save_data(
                manufacturer,
                cfg.get("Main", "local_folder_clean_data"),
                cfg.get("Main", "start_time"),
                cfg.get("Main", "end_time"),
                "clean",
            )

        upload_raw = cfg.getboolean("Main", "upload_raw_googledrive")
        upload_clean = cfg.getboolean("Main", "upload_clean_googledrive")

        if upload_raw or upload_clean:
            try:
                service = utils.auth_google_api(cfg.get("GoogleAPI", "credentials_fn"))
            except utils.GoogleAPIError:
                logging.error("Cannot connect to Google API.")
                logging.error(traceback.format_exc())
                break

            if upload_raw:
                logging.info("Uploading raw data to Google Drive.")
                upload_data_googledrive(
                    service, raw_fns, cfg.get("GoogleAPI", "raw_data_id"), "text/json"
                )

            if upload_clean:
                logging.info("Uploading clean CSV data to Google Drive.")
                upload_data_googledrive(
                    service,
                    clean_fns,
                    cfg.get("GoogleAPI", "clean_data_id"),
                    "text/csv",
                )


if __name__ == "__main__":
    main()
