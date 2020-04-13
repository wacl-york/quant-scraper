"""
    daily_preprocessing.py
    ~~~~~~~~~~~~~~~~~~~~~~

    Script that takes cleaned and validated air quality sensor data that has
    been stored to disk, and converts it into a format suitable for analysis.Unit tests

    In particular, the input data is stored:
        - Currently in 1 file per device
        - Each file is in long format, i.e. 3 columns with timestamp, measurand, 
            and measurement

    The output of this pre-processing is:
        - A single file per manufacturer containing the data from all its
        devices
        - The data will be in wide format, i.e. one column per measurand
        - Each file will contain both gases and particular matter
        - Basic resampling will be run so that every file has the same
        time resolution.
"""

import os
import logging
import configparser
import traceback

import numpy as np
import pandas as pd
import quantscraper.utils as utils
import quantscraper.cli as cli

from quantscraper.manufacturers.Aeroqual import Aeroqual
from quantscraper.manufacturers.AQMesh import AQMesh
from quantscraper.manufacturers.Zephyr import Zephyr
from quantscraper.manufacturers.MyQuantAQ import MyQuantAQ


def get_data(cfg, manufacturer, device_id, date_start, date_end):
    """
    Reads previously saved clean data into memory.

    Data is saved in 1 file per manufacturer, device, and time window.
    This function finds the file matching these parameters.
    It then adds the manufacturer and device id name as columns to the data.

    NB: If the data source switches to a database this function will
    need modifying, but otherwise the pre-processing script should remain
    intact.
    Hence the inclusion of the slightly awkward date_start and date_end
    arguments, rather than just a single day, so that when the data is stored in
    a database the SELECT query can easily WHERE date > date_start AND date <
    date_end, rather than needing to do any date-time calculations.
    Likewise why cfg is passed in when all we need is the folder name, so that
    any DB connection information can be pulled from the config object.

    Args:
        cfg (ConfigParser): ConfigParser object containing data parameters.
        manufacturer (string): Manufacturer name.
        device_id (str): Device id
        date_start (str): Starting time of the recording.
        date_end (str): Ending time of the recording.

    Returns:
        A pandas.DataFrame object.
    """
    fn = utils.CLEAN_DATA_FN.substitute(
        man=manufacturer, device=device_id, start=date_start, end=date_end
    )
    folder = cfg.get("Main", "local_folder_clean_data")
    full_path = os.path.join(folder, fn)

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


def long_to_wide(long, measurands=None):
    """
    Converts a table containing sensor data in long format into a wide table
    with 1 column per measurand.

    Args:
        long (pandas.DataFrame): DataFrame with 1 row per measurement.
            Has columns:
                - device (str)
                - timestamp (str)
                - measurand (str)
                - value (float)
        measurands (str[], optional): List of measurands that expect to have
            values. If any of these measurands don't have any clean values (and
            thus aren't present in the 'long' table), then a column is formed
            for them in the wide, filled with NaNs.

    Returns:
        A pandas.DataFrame object with columns:
            NB: The first 2 are used as a MultiIndex.
            - device (str)
            - timestamp (str)
            - Then 1 column for each measurand
    """

    # If specified measurands of interest then restrict data frame to them
    if measurands is not None:
        try:
            long = long[long["measurand"].isin(measurands)]
        except KeyError as ex:
            raise utils.DataConversionError(
                "Missing 'measurand' column in long clean data."
            )
        # Get list of unique sensors
        try:
            devices = long.device.unique()
        except AttributeError:
            raise utils.DataConversionError("There is no 'device' column available.")

    # Concatenate device and measurand, removing whitespace
    try:
        long = long.assign(measurand=long.device.map(str) + "_" + long.measurand)
        long["measurand"] = long.measurand.str.replace(" ", "", regex=True)
    except AttributeError:
        raise utils.DataConversionError(
            "Columns 'device' and 'measurand' must be available."
        )

    try:
        wide = long.pivot_table(
            index=["timestamp"],
            columns="measurand",
            values="value",
            fill_value=np.nan,  # As required
            dropna=False,
        )  # Don't want to lose columns
    except pd.core.base.DataError as ex:
        raise utils.DataConversionError("The long clean data should be all floats.")
    except KeyError as ex:
        raise utils.DataConversionError("Missing column in long clean data.")

    # Add NaN filled column for any measurand/sensor combination that wasn't in long data
    if measurands is not None:
        for measurand in measurands:
            for device in devices:
                # Generate combined column name
                comb_col = device + "_" + measurand
                comb_col = comb_col.replace(" ", "")
                if comb_col not in wide.columns:
                    wide[comb_col] = np.nan

    # Remove rows that have all NaNs
    wide.dropna(how="all", inplace=True)

    # Reorder columns alphabetically so all measurands from same device are
    # adjacent
    wide = wide.reindex(sorted(wide.columns), axis=1)

    return wide


def resample(df):
    """
    Resamples the time-serieses into a constant resolution.

    Args:
        df (pandas.DataFrame): Input data.

    Returns:
        A pandas.DataFrame object in the specified time-resolution.
    """
    return df


def main():

    # TODO Just using same setup functions as cli.py here.
    # Don't think would be appropriate to refactor these functions into the
    # utils.py module, as these are script functions, rather than library
    # functions associated with the collection of air quality data

    # Setup logging
    cli.setup_loggers(None)

    # Parse config file
    args = cli.parse_args()

    cfg = configparser.ConfigParser()
    cfg.read(args.configfilepath)

    cli.setup_scraping_timeframe(cfg)

    # Get useful properties from config
    start_window = cfg.get("Main", "start_time")
    end_window = cfg.get("Main", "end_time")
    local_folder = cfg.get("Main", "local_folder_analysis_data")
    credentials_fn = cfg.get("GoogleAPI", "credentials_fn")
    drive_analysis_id = cfg.get("GoogleAPI", "analysis_data_id")

    # Needs to iterate through all manufacturers
    manufacturers = [Aeroqual, AQMesh, Zephyr, MyQuantAQ]
    for man_class in manufacturers:
        logging.info("Manufacturer: {}".format(man_class.name))
        manufacturer = man_class(cfg)

        logging.info("Reading data from all devices...")
        dfs = []
        for device in manufacturer.device_ids:
            try:
                df = get_data(cfg, manufacturer.name, device, start_window, end_window)
            except utils.DataReadingError:
                logging.error("No clean data found for device '{}'.".format(device))
                logging.error(traceback.format_exc())
                continue

            dfs.append(df)

        # Stack data into 1 data frame for this manufacturer
        combined_df = pd.concat(dfs)

        # Convert into wide table
        try:
            logging.info("Converting to wide format.")
            wide_df = long_to_wide(combined_df, manufacturer.analysis_columns)
        except utils.DataConversionError:
            logging.error(
                "Error when converting long table for this manufacturer to wide."
            )
            logging.error(traceback.format_exc())
            continue

        # Resample into same resolution
        logging.info("Resampling time-series.")
        df_resampled = resample(wide_df)

        # Save pre-processed data frame locally
        logging.info("Saving file to disk.")
        filename = utils.ANALYSIS_DATA_FN.substitute(
            man=manufacturer.name, start=start_window, end=end_window
        )
        file_path = os.path.join(local_folder, filename)
        try:
            utils.save_dataframe(df_resampled, file_path)
        except utils.DataSavingError:
            logging.error("Error encountered when saving file to disk.")
            logging.error(traceback.format_exc())
            continue

        # Upload to GoogleDrive
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
