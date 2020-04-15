"""
    utils.py
    ~~~~~~~~

    Contains utility functions.
"""

import math
import os
import pickle
import json
import csv
import socket
from string import Template

from google.oauth2 import service_account
import googleapiclient.discovery
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

RAW_DATA_FN = Template("${man}_${device}_${start}_${end}.json")
CLEAN_DATA_FN = Template("${man}_${device}_${start}_${end}.csv")
ANALYSIS_DATA_FN = Template("${man}_${start}_${end}.csv")


class LoginError(Exception):
    """
    Custom exception class for situations where a login attempt has failed.
    """


class TimeError(Exception):
    """
    Custom exception class for errors associated with datetime formatting.
    """


class SetupError(Exception):
    """
    Custom exception class for errors associated with CLI setup.
    """


class DataDownloadError(Exception):
    """
    Custom exception class for situations where a data scrape attempt has failed.
    """


class DataParseError(Exception):
    """
    Custom exception class for situations where parsing into CSV has failed.
    """


class DataSavingError(Exception):
    """
    Custom exception class for situations where saving a file has failed.
    """


class DataReadingError(Exception):
    """
    Custom exception class for situations where reading a file from disk
    has failed.
    """


class DataUploadError(Exception):
    """
    Custom exception class for situations where uploading a file to GoogleDrive
    has failed.
    """


class ValidateDataError(Exception):
    """
    Custom exception class for situations where validating a dataset has failed.
    """


class GoogleAPIError(Exception):
    """
    Custom exception class for errors related to using Google's API.
    """


class DataConversionError(Exception):
    """
    Custom exception class for errors related to pivoting a long table to wide.
    """


class ResamplingError(Exception):
    """
    Custom exception class for errors related to resampling a time-series.
    """


def copy_object(input):
    """
    Function to deep copy a Python object.

    This pickle method should work for any Python 3 object.

    Args:
        input (Object): input object that must be serializable by pickle.

    Returns:
        A deep copy of 'input', a second ConfigParser object.
    """
    pickle_in = pickle.dumps(input)
    pickle_out = pickle.loads(pickle_in)
    return pickle_out


def summarise_validation(n_raw, counts):
    """
    Produces a text summary of the validation results.

    Args:
        n_raw (int): Number of rows in the raw CSV data.
        counts (dict): Dictionary mapping {measurand: # clean samples}

    Returns:
        A string, summarising the number of clean data points.
    """
    n_clean = counts["timestamp"]
    try:
        pct_clean = n_clean / n_raw * 100
    except ZeroDivisionError:
        pct_clean = 0

    summary = "Found {}/{} ({:.1f}%) rows with usable timestamps. Data fields: ".format(
        n_clean, n_raw, pct_clean
    )

    for measurand, measurand_clean in counts.items():
        if measurand == "timestamp":
            continue
        try:
            pct_clean = measurand_clean / n_clean * 100
        except ZeroDivisionError:
            pct_clean = 0

        measurand_str = "{} {}/{} ({:.1f}%)\t".format(
            measurand, measurand_clean, n_clean, pct_clean
        )
        summary += measurand_str
    return summary


def is_float(x):
    """
    Tests whether a given string is a float.

    Note that this function uses a relatively strict definition of float, such
    that infinity and nan are not considered floats, despite being counted as
    such by Python.

    Args:
        x (str): The input string.

    Returns:
        Boolean indicating whether x can be parsed as a float or not.
        Note it doesn't actually do the parsing into float format.
    """
    is_float = False
    try:
        val_parsed = float(x)
        # Look out for infinity and NaNs
        if math.isinf(val_parsed) or math.isnan(val_parsed):
            raise ValueError

        is_float = True

    except ValueError:
        is_float = False
    except TypeError:
        is_float = False

    return is_float


def auth_google_api(credentials_fn):
    """
    Authorizes connection to GoogleDrive API.

    Uses v3 of the GoogleDrive API, see examples at:
    https://developers.google.com/drive/api/v3/quickstart/python

    Args:
        credentials_fn (str): Path to JSON file that has Google API credentials
            saved.

    Returns:
        A googleapiclient.discovery.Resource object.
    """
    scopes = ["https://www.googleapis.com/auth/drive.file"]

    try:
        credentials = service_account.Credentials.from_service_account_file(
            credentials_fn, scopes=scopes
        )
    except FileNotFoundError:
        raise GoogleAPIError(
            "Credential file '{}' not found".format(credentials_fn)
        ) from None
    except ValueError:
        raise GoogleAPIError("Credential file is not formatted as expected") from None

    # setting cache_discovery = False removes a large amount of warnings in log,
    # that seemingly have little performance impact as we don't need cache.
    service = googleapiclient.discovery.build(
        "drive", "v3", credentials=credentials, cache_discovery=False
    )
    return service


def upload_file_google_drive(service, fn, folder_id, mime_type):
    """
    Uploads a file to a specified Google Drive folder.

    Args:
        service (googleapiclient.discovery.Resource): Google API service object.
        fn (str): Filepath of the local file to be uploaded.
        folder_id (str): ID of the target Google Drive folder.
        mime_type (str): MIME type of file.

    Returns:
        None, uploads data to Google Drive as a side effect.
    """
    # Filename should be base filename, removing path
    base_fn = os.path.basename(fn)

    file_metadata = {"name": base_fn, "mimeType": mime_type, "parents": [folder_id]}

    media = MediaFileUpload(fn, mimetype=mime_type)

    try:
        service.files().create(
            body=file_metadata, media_body=media, supportsAllDrives=True
        ).execute()
    except socket.timeout:
        raise DataUploadError("Connection timed out") from None
    except HttpError as ex:
        raise DataUploadError("HTTP error: {}.".format(ex)) from None


def save_json_file(data, filename):
    """
    Encodes data as JSON and saves it to disk.

    Args:
        - data (misc): Data in JSON-parseable format.
        - filename (str): Location to save data to

    Returns:
        None. Saves data to disk as JSON files as a side-effect.
    """
    if os.path.isfile(filename):
        raise DataSavingError("File {} already exists.".format(filename))

    try:
        with open(filename, "w") as outfile:
            json.dump(data, outfile)
    except json.decoder.JSONDecodeError:
        raise DataSavingError("Unable to serialize raw data to json.")
    except FileNotFoundError as ex:
        raise DataSavingError("Cannot save to file {}.".format(filename)) from None


def save_csv_file(data, filename):
    """
    Saves CSV data to disk.

    Args:
        - data (list): Data in CSV (2D list) format to be saved.
        - filename (str): Location to save data to

    Returns:
        None. Saves data to disk as CSV files as a side-effect.
    """
    if os.path.isfile(filename):
        raise DataSavingError("File {} already exists.".format(filename))

    try:
        with open(filename, "w") as outfile:
            writer = csv.writer(outfile, delimiter=",")
            writer.writerows(data)
    except FileNotFoundError as ex:
        raise DataSavingError("Cannot save to file {}.".format(filename)) from None


def save_dataframe(data, filename):
    """
    Saves a pandas dataframe to disk.

    Args:
        - data (pandas.DataFrame): Input data frame.
        - filename (str): Location to save data frame to.

    Returns:
        None, saves to disk as a side effect.
    """
    if os.path.isfile(filename):
        raise DataSavingError("File {} already exists.".format(filename))

    try:
        data.to_csv(filename)
    except FileNotFoundError as ex:
        raise DataSavingError("Cannot save to file {}.".format(filename)) from None
