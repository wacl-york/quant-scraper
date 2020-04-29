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
import traceback
import json
from datetime import date, timedelta, datetime

import numpy as np
import pandas as pd
import quantscraper.utils as utils
import quantscraper.cli as cli


def setup_config(cfg_fn):
    """
    Loads configuration parameters from a file into memory.

    Args:
        - cfg_fn (str): Filepath of the .ini file.

    Returns:
        A Python object, parsed from JSON.
    """
    try:
        with open(cfg_fn, "r") as in_file:
            cfg = json.load(in_file)
    except FileNotFoundError:
        raise utils.SetupError("File not found: '{}'".format(cfg_fn))
    except json.decoder.JSONDecodeError:
        raise utils.SetupError("Error parsing JSON file '{}'".format(cfg_fn))

    return cfg


def setup_scraping_timeframe(cfg):
    """
    Sets up the day to process the data for.

    By default, this script attempts to collate data from yesterday,
    although if a valid YYYY-mm-dd date is provided in the 'date' top-level
    attribute of the config JSON file then that date is used instead.

    Args:
        - cfg (Object): Contains the script configuration
            settings.

    Returns:
        Updated version of config with the 'date' field set as a valid
        date if it wasn't already.
    """
    try:
        date_dt = datetime.strptime(cfg["date"], "%Y-%m-%d")
        cfg["date"] = date_dt.strftime("%Y-%m-%d")
    except KeyError:
        yesterday = date.today() - timedelta(days=1)
        cfg["date"] = yesterday.strftime("%Y-%m-%d")
    except ValueError:
        raise utils.TimeError(
            "'{}' isn't a valid YYYY-mm-dd formatted date.".format(cfg["date"])
        )

    return cfg


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


def main():

    # Just using same setup functions as cli.py here.
    # Don't think would be appropriate to refactor these functions into the
    # utils.py module, as these are script functions, rather than library
    # functions associated with the collection of air quality data

    # Setup logging, which for now just logs to stdout
    try:
        cli.setup_loggers()
    except utils.SetupError:
        logging.error("Error in setting up loggers.")
        logging.error(traceback.format_exc())
        logging.error("Terminating program")
        sys.exit()

    # Parse args and config file
    args = cli.parse_args()
    try:
        cfg = setup_config(args.configfilepath)
    except utils.SetupError:
        logging.error("Error in setting up configuration properties")
        logging.error(traceback.format_exc())
        logging.error("Terminating program")
        sys.exit()

    # Default to yesterday's data if no parseable date provided in JSON
    cfg = setup_scraping_timeframe(cfg)

    # Get useful properties from config
    recording_date = cfg["date"]
    local_clean_folder = cfg["local_folder_clean_data"]
    local_analysis_folder = cfg["local_folder_analysis_data"]
    credentials_fn = cfg["google_api_credentials_fn"]
    drive_analysis_id = cfg["gdrive_analysis_folder_id"]
    upload_google_drive = cfg["upload_analysis_gdrive"]
    time_res = cfg["time_resolution"]

    # Load all manufacturers
    for manufacturer in cfg["manufacturers"]:

        logging.info("Manufacturer: {}".format(manufacturer["name"]))

        logging.info("Reading data from all devices...")
        dfs = []
        for device in manufacturer["devices"]:
            try:
                dataframe = get_data(
                    local_clean_folder,
                    manufacturer["name"],
                    device["name"],
                    recording_date,
                )
            except utils.DataReadingError as ex:
                logging.error(
                    "No clean data found for device '{}': {}".format(device["name"], ex)
                )
                continue

            dfs.append(dataframe)

        # Stack data into 1 data frame for this manufacturer
        try:
            combined_df = pd.concat(dfs)
        except ValueError:
            logging.error(
                "No clean data found for manufacturer '{}'.".format(
                    manufacturer["name"]
                )
            )
            continue

        # Convert into wide table
        try:
            logging.info("Converting to wide format.")
            all_devices = [dev["name"] for dev in manufacturer["devices"]]
            wide_df = long_to_wide(combined_df, manufacturer["fields"], all_devices)
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
            man=manufacturer["name"], day=recording_date
        )
        file_path = os.path.join(local_analysis_folder, filename)
        try:
            utils.save_dataframe(df_resampled, file_path)
        except utils.DataSavingError as ex:
            logging.error("Could not save file to disk: {}.".format(ex))
            continue

        # Upload to GoogleDrive
        if upload_google_drive:
            logging.info("Initiating upload to GoogleDrive.")
            try:
                service = utils.auth_google_api(credentials_fn)
            except utils.GoogleAPIError:
                logging.error("Cannot connect to Google API.")
                logging.error(traceback.format_exc())
                continue

            try:
                utils.upload_file_google_drive(
                    service, file_path, drive_analysis_id, "text/csv"
                )
                logging.info("Upload successful.")
            except utils.DataUploadError:
                logging.error("Error in upload")
                logging.error(traceback.format_exc())


if __name__ == "__main__":
    main()
