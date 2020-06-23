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
import configparser

from google.oauth2 import service_account
import googleapiclient.discovery
from googleapiclient.http import MediaFileUpload
from googleapiclient.errors import HttpError

RAW_DATA_FN = Template("${man}_${device}_${day}.json")
CLEAN_DATA_FN = Template("${man}_${device}_${day}.csv")
ANALYSIS_DATA_FN = Template("${man}_${day}.csv")

DEVICES_FN = "devices.json"


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


def copy_object(obj):
    """
    Function to deep copy a Python object.

    This pickle method should work for any Python 3 object.

    Args:
        - obj (Object): input object that must be serializable by pickle.

    Returns:
        A deep copy of obj.
    """
    pickle_in = pickle.dumps(obj)
    pickle_out = pickle.loads(pickle_in)
    return pickle_out


def is_float(x):
    """
    Tests whether a given string is a float.

    Note that this function uses a relatively strict definition of float, such
    that infinity and nan are not considered floats, despite being counted as
    such by Python.

    Args:
        - x (str): The input string.

    Returns:
        Boolean indicating whether x can be parsed as a float or not.
        Note it doesn't actually do the parsing into float, that will need to be
        run separately.
    """
    parseable = False
    try:
        val_parsed = float(x)
        # Look out for infinity and NaNs
        if math.isinf(val_parsed) or math.isnan(val_parsed):
            raise ValueError

        parseable = True

    except ValueError:
        parseable = False
    except TypeError:
        parseable = False

    return parseable


def parse_JSON_environment_variable(name):
    """
    Parses JSON keyword-value environment variable into a Python dict.

    Args:
        - name (str). Name of the JSON formatted environment variable.

    Returns:
        A dict with each keyword-value loaded.
    """
    try:
        raw_params = os.environ[name]
    except KeyError:
        raise SetupError("Environment variable {} not found.".format(name)) from None

    try:
        params = json.loads(raw_params)
    except json.decoder.JSONDecodeError:
        raise SetupError(
            "Unable to parse environment variable {} as JSON.".format(name)
        )

    return params


def auth_google_api():
    """
    Authorizes connection to GoogleDrive API.

    Requires GOOGLE_CREDS environment variable to be set, containing the
    contents of the JSON credential file, formatted as a string.

    Uses v3 of the GoogleDrive API, see examples at:
    https://developers.google.com/drive/api/v3/quickstart/python

    Args:
        None. Loads credentials from environment variable.

    Returns:
        A googleapiclient.discovery.Resource object.
    """
    scopes = ["https://www.googleapis.com/auth/drive.file"]
    try:
        params = parse_JSON_environment_variable("GOOGLE_CREDS")
    except SetupError as ex:
        raise GoogleAPIError(ex)

    try:
        credentials = service_account.Credentials.from_service_account_info(
            params, scopes=scopes
        )
    except ValueError:
        raise GoogleAPIError("Credential file is not formatted as expected") from None

    # setting cache_discovery = False removes a large amount of warnings in log,
    # that seemingly have little performance impact as we don't need cache.
    service = googleapiclient.discovery.build(
        "drive", "v3", credentials=credentials, cache_discovery=False
    )
    return service


def upload_file_google_drive(service, filepath, folder_id, mime_type):
    """
    Uploads a file to a specified Google Drive folder.

    Args:
        - service (googleapiclient.discovery.Resource): Google API service object.
        - filepath (str): Filepath of the local file to be uploaded.
        - folder_id (str): ID of the target Google Drive folder.
        - mime_type (str): MIME type of file.

    Returns:
        None, uploads data to Google Drive as a side effect.
    """
    # Filename should be base filename, removing path
    base_fn = os.path.basename(filepath)

    file_metadata = {"name": base_fn, "mimeType": mime_type, "parents": [folder_id]}

    media = MediaFileUpload(filepath, mimetype=mime_type)

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


def save_plaintext(text, filename):
    """
    Saves string directly to disk.

    Args:
        - data (str): Text to be saved.
        - filename (str): Location to save data to

    Returns:
        None. Saves text to disk as a side-effect.
    """
    if os.path.isfile(filename):
        raise DataSavingError("File {} already exists.".format(filename))

    try:
        with open(filename, "w") as outfile:
            outfile.write(text)
    except FileNotFoundError as ex:
        raise DataSavingError("Cannot save to file {}.".format(filename)) from None


def load_html_template(filename):
    """
    Loads HTML template file into memory as string.Template object.

    The file must use $placeholder formatting to be compatible with
    string.Template.

    Args:
        filename (str): Location of the HTML file.

    Returns:
        A string.Template object.
    """
    try:
        with open(filename, "r") as infile:
            template_raw = infile.read()
    except FileNotFoundError:
        raise DataReadingError("Cannot find file {}".format(filename))
    except IOError:
        raise DataReadingError("Unable to read file {}.".format(filename)) from None

    return Template(template_raw)


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
        raise SetupError("No sections found in '{}'".format(cfg_fn))

    return cfg


def load_device_configuration():
    """
    """
    try:
        with open(DEVICES_FN, "r") as infile:
            device_config = json.load(infile)
    except FileNotFoundError:
        raise SetupError("Cannot open file {}".format(DEVICES_FN)) from None
    except json.decoder.JSONDecodeError:
        raise SetupError("Cannot parse file {} into JSON".format(DEVICES_FN)) from None

    return device_config
