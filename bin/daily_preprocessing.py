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
        - cfg (configparser.Namespace): ConfigParser object containing data parameters.
        - manufacturer (string): Manufacturer name.
        - device_id (str): Device id
        - date_start (str): Starting time of the recording.
        - date_end (str): Ending time of the recording.

    Returns:
        A pandas.DataFrame object.
    """
    data_fn = utils.CLEAN_DATA_FN.substitute(
        man=manufacturer, device=device_id, start=date_start, end=date_end
    )
    folder = cfg.get("Main", "local_folder_clean_data")
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


def long_to_wide(long, measurands=None):
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

    Returns:
        A pandas.DataFrame object with columns:
            - timestamp (pandas.datetime type, the DataFrame index)
            - Then 1 column for each measurand/device pair, labelled
                <measurand_device>.
    """

    # If specified measurands of interest then restrict data frame to them
    if measurands is not None:
        try:
            long = long[long["measurand"].isin(measurands)]
        except KeyError:
            raise utils.DataConversionError(
                "Missing 'measurand' column in long clean data."
            ) from None
        # Get list of unique sensors
        try:
            devices = long.device.unique()
        except AttributeError:
            raise utils.DataConversionError(
                "There is no 'device' column available."
            ) from None

    # Concatenate device and measurand, removing whitespace
    try:
        long = long.assign(measurand=long.measurand.map(str) + "_" + long.device)
        long["measurand"] = long.measurand.str.replace(" ", "", regex=True)
    except AttributeError:
        raise utils.DataConversionError(
            "Columns 'device' and 'measurand' must be available."
        )

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
    except KeyError:
        raise utils.DataConversionError("Missing column in long clean data.")

    # Add NaN filled column for any device/measurand combination that wasn't in long data
    if measurands is not None:
        for measurand in measurands:
            for device in devices:
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
        cfg = cli.setup_config(args.configfilepath)
    except utils.SetupError:
        logging.error("Error in setting up configuration properties")
        logging.error(traceback.format_exc())
        logging.error("Terminating program")
        sys.exit()

    cli.setup_scraping_timeframe(cfg)

    # Get useful properties from config
    start_window = cfg.get("Main", "start_time")
    end_window = cfg.get("Main", "end_time")
    local_folder = cfg.get("Main", "local_folder_analysis_data")
    credentials_fn = cfg.get("GoogleAPI", "credentials_fn")
    drive_analysis_id = cfg.get("GoogleAPI", "analysis_data_id")
    upload_google_drive = cfg.getboolean("Main", "upload_analysis_googledrive")

    # Needs to iterate through all manufacturers
    manufacturers = [Aeroqual, AQMesh, Zephyr, MyQuantAQ]
    for man_class in manufacturers:
        logging.info("Manufacturer: {}".format(man_class.name))
        manufacturer = man_class(cfg)

        logging.info("Reading data from all devices...")
        dfs = []
        for device in manufacturer.device_ids:
            try:
                dataframe = get_data(
                    cfg, manufacturer.name, device, start_window, end_window
                )
            except utils.DataReadingError:
                logging.error("No clean data found for device '{}'.".format(device))
                logging.error(traceback.format_exc())
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
            analysis_columns = [
                m["clean_label"]
                for m in manufacturer.measurands
                if m["included_analysis"]
            ]
            wide_df = long_to_wide(combined_df, analysis_columns)
        except utils.DataConversionError:
            logging.error(
                "Error when converting long table for this manufacturer to wide."
            )
            logging.error(traceback.format_exc())
            continue

        # Resample into same resolution
        time_res = cfg.get("Analysis", "time_resolution")
        logging.info(
            "Resampling time-series with a resolution of '{}'.".format(time_res)
        )
        try:
            df_resampled = resample(wide_df, time_res)
        except utils.ResamplingError:
            logging.error(
                "Error in resampling data, raw frequency will be used instead."
            )
            logging.error(traceback.format_exc())
            df_resampled = wide_df

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
