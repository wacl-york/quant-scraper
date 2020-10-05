#!/usr/bin/env python3
"""
    daily_preprocessing.py
    ~~~~~~~~~~~~~~~~~~~~~~

    Script that takes cleaned and validated air quality sensor data that has
    been stored to disk, and converts it into a format suitable for analysis.

    In particular, the input data is stored:
        - In 1 file per device
        - Each file is in long format, i.e. 3 columns with timestamp, measurand,
            and measurement

    The output of this pre-processing is:
        - A single file per manufacturer containing the data from all its
            devices
        - The data will be in wide format, i.e. one column per measurand/device
            pair
        - Each file will contain both gases and particular matter
        - Basic resampling will be run so that every file has the same
            time resolution
"""

import sys
import os
import logging
import argparse
import traceback
import json
from datetime import date, timedelta, datetime
import numpy as np
import pandas as pd

import quantscraper.utils as utils
from quantscraper.factories import setup_manufacturers


def parse_args():
    """
    Parses CLI arguments to the script.

    Args:
        - None

    Returns:
        An argparse.Namespace object.
    """
    parser = argparse.ArgumentParser(description="QUANT preprocessing")
    parser.add_argument(
        "--devices",
        metavar="DEVICE1 DEVICE2 ... DEVICEN",
        nargs="+",
        help="Specify the device IDs to include in the scraping. If not provided then all the devices specified in the configuration file are scraped.",
    )

    parser.add_argument(
        "--date",
        metavar="DATE",
        help="The date to collate data from, in the format YYY-mm-dd. Defaults to yesterday.",
    )

    parser.add_argument(
        "--upload",
        action="store_true",
        help="Uploads the pre-processed data to Google Drive.",
    )

    args = parser.parse_args()
    return args


def setup_scraping_timeframe(date_format, day=None):
    """
    Sets up the day to process the data for.

    By default, this script attempts to collate data from yesterday,
    although if a valid date is passed in to the `day` argument then that value
    is used after checking that it is parseable.

    Args:
        - date_format (str): The time format in which dates are encoded in
            filenames by QUANT.
        - day (str, optional): The day to run the pre-processing routine for.
            Must be formatted as date_format.
            If not provided then defaults to yesterday's date.

    Returns:
        The date to process for as a string encoded as date_format.
    """
    if day is None:
        yesterday = date.today() - timedelta(days=1)
        day = yesterday.strftime(date_format)

    # Ensure that the day is a valid date
    try:
        date_dt = datetime.strptime(day, date_format)
    except ValueError:
        raise utils.TimeError(
            "'{}' cannot be parsed by format {}.".format(day, date_format)
        )

    date_str = date_dt.strftime(date_format)
    return date_str


def get_data(folder, manufacturer, device_id, day):
    """
    Reads previously saved clean data into memory.

    Data is saved in 1 file per manufacturer, device, and time window.
    This function finds the file matching these parameters.
    It then adds the manufacturer and device id name as columns to the data.

    Args:
        - folder (str): Folder where the data is saved.
        - manufacturer (string): Manufacturer name.
        - device_id (str): Device id
        - day (str): Recording date, in "YYYY-MM-DD" format.

    Returns:
        A pandas.DataFrame object.
    """
    data_fn = utils.CLEAN_DATA_FN.substitute(
        man=manufacturer, device=device_id, day=day
    )
    full_path = os.path.join(folder, data_fn)

    try:
        data = pd.read_csv(full_path)
    except FileNotFoundError:
        raise utils.DataReadingError("File not found '{}'.".format(full_path)) from None
    except pd.errors.EmptyDataError:
        raise utils.DataReadingError("Empty file '{}'.".format(full_path)) from None

    # Add device ID column and parse timestamp as datetime
    data["device"] = device_id
    data["timestamp"] = pd.to_datetime(data["timestamp"])

    return data


def long_to_wide(long, measurands=None, devices=None):
    """
    Converts a table containing sensor data in long format into a wide table
    with 1 column per measurand/device pair.

    It firstly combines the measurands into a device/measurand pair in the long
    format, and then pivots into a wide table so that each column is of the form
    <measurand_device> and each row corresponds to a unique time-point.

    Args:
        - long (pandas.DataFrame): DataFrame with 1 row per measurement.
              Has columns:
                  - device (str)
                  - timestamp (str)
                  - measurand (str)
                  - value (float)
        - measurands (str[], optional): List of measurands to include in the
            output file. If not provided then all the measurands in 'long' are
            kept. If provided then 'long' is firstly restricted to measurands in
            this list, then NaN filled columns are made for any requested measurands in
            'measurands' that don't have any observations in 'long'.
        - devices (str[], optional): List of devices to include in the
            output file. If not provided then all the devices in 'long' are
            kept. If provided then 'long' is firstly restricted to devices in
            this list, then NaN filled columns are made for any requested
            devices in 'devices' that don't have any observations in 'long'.

    Returns:
        A pandas.DataFrame object with columns:
            - timestamp (pandas.datetime type, the DataFrame index)
            - Then 1 column for each measurand/device pair, labelled
                <measurand_device>.
    """

    def guard_column(col):
        if not col in long.columns:
            raise utils.DataConversionError(
                "Column '{}' must be available.".format(col)
            )

    guard_column("device")
    guard_column("measurand")
    guard_column("timestamp")
    guard_column("value")

    # If specified measurands and/or devices, restrict data frame to them
    if measurands is not None:
        long = long[long["measurand"].isin(measurands)]
        selected_measurands = measurands
    else:
        selected_measurands = long.measurand.unique()

    if devices is not None:
        long = long[long["device"].isin(devices)]
        selected_devices = devices
    else:
        selected_devices = long.device.unique()

    # Concatenate device and measurand, removing whitespace
    long = long.assign(measurand=long.measurand.map(str) + "_" + long.device)
    long["measurand"] = long.measurand.str.replace(" ", "", regex=True)

    # Pivot to wide table
    try:
        wide = long.pivot_table(
            index=["timestamp"],
            columns="measurand",
            values="value",
            fill_value=np.nan,  # As required
            dropna=False,
        )  # Don't want to lose columns
    except pd.core.base.DataError:
        raise utils.DataConversionError(
            "The long clean data should be all floats."
        ) from None

    # Add NaN filled column for any device/measurand combination that wasn't in long data
    if measurands is not None or devices is not None:
        for measurand in selected_measurands:
            for device in selected_devices:
                # Generate combined column name
                comb_col = measurand + "_" + device
                comb_col = comb_col.replace(" ", "")
                if comb_col not in wide.columns:
                    wide[comb_col] = np.nan

    # Remove rows that have all NaNs
    wide.dropna(how="all", inplace=True)

    # Reorder columns alphabetically so all measurands are adjacent
    wide = wide.reindex(sorted(wide.columns), axis=1)

    return wide


def resample(dataframe, resolution):
    """
    Resamples the time-series into a constant resolution.

    Uses the pandas.resample() function that groups all points into bins at the
    specified resolution, then aggregates them to obtain a single value.
    In this usage, the aggregation function is the mean.

    Args:
        dataframe (pandas.DataFrame): Input data.
        resolution (str): Desired output resolution, see following link for
            syntax:
            https://pandas.pydata.org/pandas-docs/stable/user_guide/timeseries.html#dateoffset-objects
    Returns:
        A pandas.DataFrame object in the specified time-resolution.
    """
    try:
        df_resampled = dataframe.resample(resolution).mean()
    except TypeError:
        raise utils.ResamplingError("Data doesn't have a time index.") from None
    except ValueError:
        raise utils.ResamplingError(
            "'{}' isn't a valid time resolution format.".format(resolution)
        ) from None

    return df_resampled


def upload_files_google_drive(files):
    """
    Provides boiler plate code and error handling for all aspects of uploading a
    list of files to Google Drive, including:
        - Initiating connection to GoogleDrive API
        - Obtaining the folder ID from an environment variable
        - Calling the function that handles the file upload.

    Args:
        - files (str[]): List of local file-path of files to be uploaded.

    Returns:
        None. Uploads files to Google Drive as a side-effect.
    """
    try:
        service = utils.auth_google_api()
    except utils.GoogleAPIError:
        logging.error("Cannot connect to Google API.")
        logging.error(traceback.format_exc())
        return

    try:
        drive_analysis_id = os.environ["GDRIVE_ANALYSIS_ID"]
    except KeyError:
        logging.error(
            "GDRIVE_ANALYSIS_ID env var not found. Please set it with the ID of the Google Drive folder to upload the analysis data to."
        )
        return

    for file in files:
        try:
            utils.upload_file_google_drive(service, file, drive_analysis_id, "text/csv")
            logging.info("Upload successful.")
        except utils.DataUploadError:
            logging.error("Error in upload")
            logging.error(traceback.format_exc())


def main():
    # Just using same setup functions as cli.py here.
    # Don't think would be appropriate to refactor these functions into the
    # utils.py module, as these are script functions, rather than library
    # functions associated with the collection of air quality data

    # Setup logging, which for now just logs to stdout
    try:
        utils.setup_loggers()
    except utils.SetupError:
        print("Error in setting up loggers.")
        print(traceback.format_exc())
        print("Terminating program")
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

    # Parse args and config file
    args = parse_args()
    try:
        cfg = utils.setup_config()
    except utils.SetupError:
        logging.error("Error in setting up configuration properties")
        logging.error(traceback.format_exc())
        logging.error("Terminating program")
        sys.exit()

    # Load config params
    local_clean_folder = cfg.get("Main", "local_folder_clean_data")
    local_analysis_folder = cfg.get("Analysis", "local_folder_analysis_data")
    time_res = cfg.get("Analysis", "time_resolution")
    date_format = cfg.get("Main", "filename_date_format")

    # Default to yesterday's data if no parseable date provided in config
    recording_date = setup_scraping_timeframe(date_format, args.date)

    try:
        device_config = utils.load_device_configuration()
    except utils.SetupError as ex:
        logging.error("Cannot load device configuration: {}.".format(ex))
        sys.exit()

    # Load all selected devices
    manufacturers = setup_manufacturers(device_config["manufacturers"], args.devices)

    files_to_upload = []

    # Load all manufacturers
    for manufacturer in manufacturers:

        logging.info("Manufacturer: {}".format(manufacturer.name))

        logging.info("Reading data from all devices...")
        dfs = []
        for device in manufacturer.devices:
            try:
                dataframe = get_data(
                    local_clean_folder,
                    manufacturer.name,
                    device.device_id,
                    recording_date,
                )
            except utils.DataReadingError as ex:
                logging.error(
                    "No clean data found for device '{}': {}".format(
                        device.device_id, ex
                    )
                )
                continue

            dfs.append(dataframe)

        # Stack data into 1 data frame for this manufacturer
        try:
            combined_df = pd.concat(dfs)
        except ValueError:
            logging.error(
                "No clean data found for manufacturer '{}'.".format(manufacturer.name)
            )
            continue

        # Convert into wide table
        try:
            logging.info("Converting to wide format.")
            # Obtain the available devices and measurands for this manufacturer,
            # and ask that the output has a column for each combination of these
            devices_to_include = [dev.device_id for dev in manufacturer.devices]
            measurands_to_include = [
                m["id"] for m in manufacturer.measurands if m["include_analysis"]
            ]
            wide_df = long_to_wide(
                combined_df, measurands_to_include, devices_to_include
            )

        except utils.DataConversionError as ex:
            logging.error("Error when converting wide to long table: {}".format(ex))
            continue

        # Resample into same resolution
        logging.info(
            "Resampling time-series with a resolution of '{}'.".format(time_res)
        )
        try:
            df_resampled = resample(wide_df, time_res)
        except utils.ResamplingError as ex:
            logging.error(
                "Error in resampling data: {}. Original frequency will be used instead.".format(
                    ex
                )
            )
            df_resampled = wide_df

        # Save pre-processed data frame locally
        logging.info("Saving file to disk.")
        filename = utils.ANALYSIS_DATA_FN.substitute(
            man=manufacturer.name, day=recording_date
        )
        file_path = os.path.join(local_analysis_folder, filename)
        try:
            utils.save_dataframe(df_resampled, file_path)
        except utils.DataSavingError as ex:
            logging.error("Could not save file to disk: {}.".format(ex))
            continue

        if args.upload:
            files_to_upload.append(file_path)

    # Upload files to Google Drive
    if args.upload and len(files_to_upload) > 0:
        logging.info("Initiating upload to GoogleDrive.")
        upload_files_google_drive(files_to_upload)


if __name__ == "__main__":
    main()
