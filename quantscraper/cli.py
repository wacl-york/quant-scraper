#!/usr/bin/env python3
"""
    cli.py
    ~~~~~~

    Main scraper script that collects data from each of the four manufacturers.
    By default it obtains all data from midnight to the following midnight of
    the previous day.  This behaviour can be changed in the config.ini file,
    which is also where credentials are stored.
"""
import logging
import argparse
import os
import sys
import configparser
from datetime import date, timedelta, datetime, time
import traceback

import quantscraper.utils as utils
from quantscraper.manufacturers.manufacturer_factory import manufacturer_factory


def setup_loggers(logfn=None):
    """
    Configures loggers.

    By default, the error log is printed to standard out,
    although it can be saved to file in addition.

    Args:
        - logfn (str, optional): File to save log to. If None then doesn't write log to file.

    Returns:
        None. the logger is accessed by the global module `logging`.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    log_fmt = logging.Formatter(
        "%(asctime)-8s:%(levelname)s: %(message)s", datefmt="%Y-%m-%d,%H:%M:%S"
    )
    cli_logger = logging.StreamHandler()
    cli_logger.setFormatter(log_fmt)
    root_logger.addHandler(cli_logger)

    if not logfn is None:
        if os.path.isfile(logfn):
            raise utils.SetupError(
                ("Log file {} already exists. " "Halting execution.").format(logfn)
            )
        file_logger = logging.FileHandler(logfn)
        file_logger.setFormatter(log_fmt)
        root_logger.addHandler(file_logger)


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


def setup_config(cfg_fn):
    """
    Loads configuration parameters from a file into memory.

    Args:
        - cfg_fn (str): Filepath of the .ini file.

    Returns:
        A configparser.Namespace instance.
    """
    cfg = configparser.ConfigParser()
    cfg.read(cfg_fn)

    if len(cfg.sections()) == 0:
        raise utils.SetupError("No sections found in '{}'".format(cfg_fn))

    return cfg


def setup_scraping_timeframe(cfg):
    """
    Sets up the scraping timeframe for the scraping run.

    By default, this script attempts to scrape from midnight of the day prior to
    the script being executed, to 1 second before the following midnight.
    I.e. if the script is run at 2020-01-08 15:36:00, then the default scraping
    window is between 2020-01-07 00:00:00 and 2020-01-07 23:59:59.

    If the Main.start_time and Main.end_time configuration parameters in the
    ini file are supplied then this default behaviour is overruled.

    Args:
        - cfg (configparser.Namespace): Contains the script configuration
            settings.

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
    Scrapes data for all devices belonging to a manufacturer.

    Args:
        - manufacturer (Manufacturer): Instance of a sub-class of Manufacturer.

    Returns:
        None, updates the Manufacturer.raw_data attribute if the download is
        successful.
    """
    for webid, devid in zip(manufacturer.device_web_ids, manufacturer.device_ids):
        try:
            manufacturer.raw_data[devid] = manufacturer.scrape_device(webid)
            logging.info("Download successful for device {}.".format(devid))
        except utils.DataDownloadError:
            logging.error("Unable to download data for device {}.".format(devid))
            logging.error(traceback.format_exc())
            manufacturer.raw_data[devid] = None


def process(manufacturer):
    """
    For each device belonging to a manufacturer, the raw JSON data is parsed
    into CSV format, before running a data cleaning proecedure to store only
    valid floating point values.

    Updates the Manufacturer.clean_data attribute if the CSV parse and
    subsequent QA validation procedures are successful.

    Args:
        - manufacturer (Manufacturer): Instance of a sub-class of Manufacturer.

    Returns:
        A dictionary summarising how many recordings are available for each
        device. Has the keys:
          - 'manufacturer': Provides manufacturer name as a string
          - 'devices': A further dict mapping {device_id : num_available_timepoints}
            If a device has no available recordings then the value is None.
    """
    summary = {"manufacturer": manufacturer.name, "devices": {}}
    for devid in manufacturer.device_ids:
        summary["devices"][devid] = None

        if manufacturer.raw_data[devid] is None:
            manufacturer.clean_data[devid] = None
            continue

        try:
            csv_data = manufacturer.parse_to_csv(manufacturer.raw_data[devid])
            num_timepoints = len(csv_data) - 1
            if num_timepoints > 0:
                logging.info(
                    "CSV parse successful for device {}. Measurements at {} time-points have been recorded.".format(
                        devid, num_timepoints
                    )
                )
            else:
                logging.error(
                    "No time-points have been found in the parsed CSV for device {}.".format(
                        devid
                    )
                )
                manufacturer.clean_data[devid] = None
                continue

        except utils.DataParseError as ex:
            logging.error(
                "Unable to parse data into CSV for device {}: {}".format(devid, ex)
            )
            manufacturer.clean_data[devid] = None
            continue

        try:
            clean_data, measurand_summary = manufacturer.validate_data(csv_data)
            manufacturer.clean_data[devid] = clean_data

            summary["devices"][devid] = {
                "timepoints": num_timepoints,
                "measurands": measurand_summary,
            }

        except utils.ValidateDataError as ex:
            logging.error("Data validation error for device {}: {}".format(devid, ex))
            manufacturer.clean_data[devid] = None

    return summary


def save_data(manufacturer, folder, day, data_type):
    """
    Iterates through all a manufacturer's devices and saves their raw or clean data to disk.

    Uses the following template filename:

    <manufacturer_name>_<deviceid>_<start_timeframe>_<end_timeframe>.<json/csv>

    Args:
        - manufacturer (Manufacturer): Instance of Manufacturer.
        - folder (str): Directory where files should be saved to.
        - day (str): Today's date, in YYYY-MM-DD format.
        - data_type (str): Either 'raw' or 'clean' to indicate which data is being
            saved.

    Returns:
        List of filenames that were successfully saved.
    """
    fns = []

    if data_type == "clean":
        fn_template = utils.CLEAN_DATA_FN
        manufacturer_data = manufacturer.clean_data
        saving_function = utils.save_csv_file
    elif data_type == "raw":
        fn_template = utils.RAW_DATA_FN
        manufacturer_data = manufacturer.raw_data
        saving_function = utils.save_json_file
    else:
        raise utils.DataSavingError("Unknown data type '{}'.".format(data_type))

    if not os.path.isdir(folder):
        raise utils.DataSavingError(
            "Folder {} doesn't exist, cannot save raw data.".format(folder)
        )

    for devid in manufacturer.device_ids:
        out_fn = fn_template.substitute(man=manufacturer.name, device=devid, day=day)

        data = manufacturer_data[devid]
        if data is None:
            continue

        full_path = os.path.join(folder, out_fn)
        logging.info("Writing file: {}".format(full_path))
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


def summarise_run(summaries):
    """
    Prints a summary of the run to the logger.

    For each manufacturer, the following information is displayed to screen:
        - How many devices had available data
        - The IDs of any devices that didn't record a single clean data point
        - A table showing the number of clean recordings of each measurand

    Args:
        summaries (list): A list of dictionaries, with each entry storing
            information about a different manufacturer.
            Each dictionary summarises how many recordings are available for each
            device. Has the keys:
              - 'manufacturer': Provides manufacturer name as a string
              - 'devices': A further dict mapping {device_id : num_available_timepoints}
                If a device has no available recordings then the value is None.

    Returns:
        None, prints text to the logger as a side-effect.
    """
    logging.info("+" * 80)
    logging.info("Summary")
    logging.info("-" * 80)
    for manu in summaries:
        logging.info(manu["manufacturer"])
        logging.info("~" * len(manu["manufacturer"]))
        avail_devices = [(d, v) for d, v in manu["devices"].items() if v is not None]
        missing_devices = [
            devid for devid, n_rows in manu["devices"].items() if n_rows is None
        ]
        logging.info(
            "{}/{} selected devices had available data over the specified time period.".format(
                len(avail_devices), len(manu["devices"])
            )
        )

        if len(missing_devices) > 0:
            logging.info(
                "Devices with no available data: {}.".format(", ".join(missing_devices))
            )

        if len(avail_devices) > 0:
            # Get header row for table, with timestamp first then alphabetically
            measurands = list(avail_devices[0][1]["measurands"].keys())
            measurands.remove("timestamp")
            measurands.sort()
            measurands.insert(0, "timestamp")
            col_names = measurands.copy()
            col_names[0] = "Timestamps"
            col_names.insert(0, "Device ID")

            # Give each column 11 chars, should be sufficient
            row_format = "{:>11}|" * (len(col_names))

            # Format and log header with horizontal lines above and below
            header_row = row_format.format(*col_names)
            logging.info("-" * len(header_row))
            logging.info("|" + header_row)
            logging.info("-" * len(header_row))

            # Print one device on each row
            for device in avail_devices:
                # Form a list with device ID + measurements in same order as
                # column header
                num_timestamps = device[1]["measurands"]["timestamp"]
                row = [device[0]]
                for m in measurands:
                    n_clean = device[1]["measurands"][m]
                    if m == "timestamp":
                        col = str(n_clean)
                    else:
                        col = "{} ({:.0f}%)".format(
                            n_clean, n_clean / num_timestamps * 100
                        )
                    row.append(col)
                # Print row to log
                logging.info("|" + row_format.format(*row))
        # Table end horizontal line
        logging.info("-" * len(header_row))
    # Summary end horizontal line
    logging.info("+" * 80)


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

    # Store device availability summary for each manufacturer
    summaries = []

    man_strings = cfg.get("Main", "manufacturers").split(",")
    for man_class in man_strings:
        logging.info("Manufacturer: {}".format(man_class))
        try:
            manufacturer = manufacturer_factory(man_class, cfg)
        except utils.DataParseError:
            logging.error("Error instantiating Manufacturer instance.")
            logging.error(traceback.format_exc())
            continue
        except KeyError as ex:
            logging.error("Error instantiating Manufacturer instance.")
            logging.error(traceback.format_exc())
            continue

        try:
            logging.info("Attempting to connect...")
            manufacturer.connect()
            logging.info("Connection established")
        except utils.LoginError:
            logging.error(
                "Cannot establish connection to {}.".format(manufacturer.name)
            )
            logging.error(traceback.format_exc())
            continue

        logging.info("Downloading data from all devices:")
        scrape(manufacturer)
        logging.info("Processing raw data for all devices:")
        man_summary = process(manufacturer)
        summaries.append(man_summary)

        # Get start time date for naming output files
        start_dt = datetime.fromisoformat(cfg.get("Main", "start_time"))
        start_fmt = start_dt.strftime("%Y-%m-%d")

        if cfg.getboolean("Main", "save_raw_data"):
            logging.info("Saving raw data from all devices:")
            raw_fns = save_data(
                manufacturer,
                cfg.get("Main", "local_folder_raw_data"),
                start_fmt,
                "raw",
            )

        if cfg.getboolean("Main", "save_clean_data"):
            logging.info("Saving cleaned CSV data from all devices:")
            clean_fns = save_data(
                manufacturer,
                cfg.get("Main", "local_folder_clean_data"),
                start_fmt,
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
                logging.info("Uploading raw data to Google Drive:")
                upload_data_googledrive(
                    service, raw_fns, cfg.get("GoogleAPI", "raw_data_id"), "text/json"
                )

            if upload_clean:
                logging.info("Uploading clean CSV data to Google Drive:")
                upload_data_googledrive(
                    service,
                    clean_fns,
                    cfg.get("GoogleAPI", "clean_data_id"),
                    "text/csv",
                )

    summarise_run(summaries)


if __name__ == "__main__":
    main()
