#!/usr/bin/env python3
"""
    preprocess_purpleair.py
    ~~~~~~~~~~~~~~~~~~~~~~~

    Generates the Analysis files for downloaded Clean PurpleAir data.

    It identifies which dates of validated data are available in a local
    directory and that have not already been pre-processed and uploaded into the
    Analysis Google Drive folder.

    It then calls the main quant_preprocess script to handle the actual
    pre-processing.
"""

import subprocess
import glob
import sys
import os
import logging
import traceback

import quantscraper.utils as utils


def main():
    """
    The main function and the only entry point into the script.

    Args:
        None
    
    Returns:
        None
    """
    try:
        utils.setup_loggers()
    except utils.SetupError:
        print("Error in setting up loggers.")
        print(traceback.format_exc())
        sys.exit()

    # This sets up environment variables if they are explicitly provided in a .env
    # file. If system env variables are present (as they will be in production),
    # then it doesn't overwrite them
    if not utils.parse_env_vars("QUANT_CREDS"):
        logging.error(
            "Error when initiating environment variables, terminating execution."
        )
        logging.error(traceback.format_exc())
        sys.exit()

    try:
        analysis_drive_id = os.environ["GDRIVE_ANALYSIS_ID"]
        toplevel_drive_id = os.environ["GDRIVE_QUANTSHARED_ID"]
    except KeyError:
        logging.error(
            "Ensure the env vars 'GDRIVE_ANALYSIS_ID' and 'GDRIVE_QUANTSHARED_ID' are set prior to running this program."
        )
        sys.exit()

    try:
        cfg = utils.setup_config()
    except utils.SetupError:
        logging.error("Error in setting up configuration properties")
        logging.error(traceback.format_exc())
        sys.exit()

    # Load device configuration
    try:
        device_config = utils.load_device_configuration()
    except utils.SetupError as ex:
        logging.error("Cannot load device configuration: {}.".format(ex))
        sys.exit()

    # Connect to Google Drive API
    try:
        # Permission to access files outside of those created by this service
        service = utils.auth_google_api(
            scopes=["https://www.googleapis.com/auth/drive"]
        )
    except utils.GoogleAPIError:
        logging.error("Cannot connect to Google API.")
        logging.error(traceback.format_exc())
        sys.exit()

    # Identify dates that have clean data for locally and are not in the Analysis GDrive dir
    logging.info(
        "Looking for dates with locally available Clean data but no uploaded Analysis data..."
    )
    uploaded_dates = get_uploaded_analysis_dates(
        service, toplevel_drive_id, analysis_drive_id
    )
    clean_dates = get_available_clean_dates(cfg.get("Main", "local_folder_clean_data"))
    dates_to_upload = sorted(
        [date for date in clean_dates if date not in uploaded_dates]
    )

    logging.info(
        f"Found {len(dates_to_upload)} dates with Clean data that will be pre-processed into Analysis files"
    )

    # Main OS call to run preprocessing. Will ask for just the PurpleAir devices
    # and will run it for each day
    pa_device_ids = get_pa_device_ids(device_config)
    preprocess_call = [
        "quant_preprocess",
        "--upload",
        "--devices",
        *pa_device_ids,
    ]
    for date in dates_to_upload:
        logging.info(f"Calling quant_preprocess with date {date}")
        call = preprocess_call + (["--date", date])
        subprocess.run(call)


def get_available_clean_dates(dir):
    """
    Obtains the dates that have at least 1 available validated PurpleAir
    recording from.

    Assumes files are saved in the standard QUANT naming convention of
    manufacturer_deviceid_date.csv

    Args:
        - dir (str): Directory where the files are saved.

    Returns:
        A list of dates as YYYY-mm-dd strings.
    """
    fns = glob.glob("{}/PurpleAir*".format(dir))
    clean_dates = list(set([get_date_from_clean_fn(file) for file in fns]))
    clean_dates = [x for x in clean_dates if x is not None]
    return clean_dates


def get_uploaded_analysis_dates(service, drive_id, analysis_id):
    """
    Obtains the dates that have already pre-processed PurpleAir data for.

    Args:
        - service (googleapiclient.discovery.Resource): Handle to GoogleAPI.
        - drive_id (str): The ID of the top-level QUANT shared drive.
        - analysis_id (str): The ID of the QUANT Clean data repository.

    Returns:
        A list of dates as YYYY-mm-dd strings.
    """
    q = f"mimeType='text/csv' and '{analysis_id}' in parents and name contains 'PurpleAir'"
    files = utils.list_files_googledrive(service, drive_id, query=q)
    dates = [get_date_from_analysis_fn(file["name"]) for file in files]
    dates = [x for x in dates if x is not None]
    return dates


def get_date_from_clean_fn(fn):
    """
    Obtains the recording date from the QUANT Clean filename convention:
        manufacturer_deviceid_date.csv

    Args:
        - fn (str): The filename.

    Returns:
        The date in YYYY-mm-dd format as a string.
    """
    # Remove folder and file extension fn = os.path.basename(fn)
    try:
        fn = os.path.basename(fn)
        fn = os.path.splitext(fn)[0]
        date = fn.split("_")[2]
    except IndexError:
        return None
    else:
        return date


def get_date_from_analysis_fn(fn):
    """
    Obtains the recording date from the QUANT analysis filename convention:
        manufacturer_date.csv

    Args:
        - fn (str): The filename.

    Returns:
        The date in YYYY-mm-dd format as a string.
    """
    # Remove folder and file extension
    try:
        fn = os.path.basename(fn)
        fn = os.path.splitext(fn)[0]
        date = fn.split("_")[1]
    except IndexError:
        return None
    else:
        return date


def get_pa_device_ids(device_config):
    """
    Gets the current PurpleAir device IDs.

    Args:
        - device_config (dict): The manufacturer and device JSON representation.

    Returns:
        A list of strings containing the device IDs.
    """
    pa_config = [m for m in device_config["manufacturers"] if m["name"] == "PurpleAir"][
        0
    ]
    pa_device_ids = [device["id"] for device in pa_config["devices"]]
    return pa_device_ids


if __name__ == "__main__":
    main()
