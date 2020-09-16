"""
    utils.py
    ~~~~~~~~

    Contains utility functions.
"""

import io
import math
import os
import pickle
import json
import csv
import socket
from string import Template
import configparser
import logging
from datetime import datetime

import boto3
from botocore.exceptions import ClientError
from google.oauth2 import service_account
import googleapiclient.discovery
from googleapiclient.http import MediaFileUpload, MediaIoBaseDownload
from googleapiclient.errors import HttpError
from dotenv import load_dotenv

RAW_DATA_FN = Template("${man}_${device}_${day}.json")
CLEAN_DATA_FN = Template("${man}_${device}_${day}.csv")
ANALYSIS_DATA_FN = Template("${man}_${day}.csv")
AVAILABILITY_DATA_FN = Template("availability_${man}_${date}.csv")

DEVICES_FN = "devices.json"
CONFIG_FN = "config.ini"


class LoginError(Exception):
    """
    Custom exception class for situations where a login attempt has failed.
    """


class EmailSendingError(Exception):
    """
    Custom exception class for situations where an email didn't send.
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


def auth_google_api(scopes=["https://www.googleapis.com/auth/drive.file"]):

    """
    Authorizes connection to GoogleDrive API.

    Requires GOOGLE_CREDS environment variable to be set, containing the
    contents of the JSON credential file, formatted as a string.

    Uses v3 of the GoogleDrive API, see examples at:
    https://developers.google.com/drive/api/v3/quickstart/python

    Args:
        - scope (list): The permissions scope of this connection. Defaults to
        view and manage files created by the service. See full docs at
        https://developers.google.com/identity/protocols/oauth2/scopes#drive

    Returns:
        A googleapiclient.discovery.Resource object.
    """
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
    except AttributeError as ex:
        raise DataUploadError("Service account not authenticated") from None


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
    Saves a pandas dataframe to disk as CSV.

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


def setup_config():
    """
    Loads configuration parameters from a file into memory.

    Args:
        None. The configuration filename is available as a global variable.

    Returns:
        A configparser.Namespace instance.
    """
    cfg = configparser.ConfigParser()
    cfg.read(CONFIG_FN)

    if len(cfg.sections()) == 0:
        raise SetupError("No sections found in '{}'".format(CONFIG_FN))

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


# TODO Make tests for this function
def download_file(service, file_id):
    """
    Downloads a given file from Google Drive.

    Args:
        - service (googleapiclient.discovery.Resource): Handle to GoogleAPI.
        - file_id (str): ID of the file to download.

    Returns:
        The file contents as a bytestream.
    """
    request = service.files().get_media(fileId=file_id)
    fh = io.BytesIO()
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while done is False:
        status, done = downloader.next_chunk()
    return fh


# TODO Make tests
def list_files_googledrive(service, drive_id, query=None):
    """
    Lists files that meet a certain criteria stored in a specific Google Drive.

    Args:
        - service (googleapiclient.discovery.Resource): Handle to GoogleAPI.
        - drive_id (str): ID of the top-level Drive directory where to search.
        - query (str, optional): Optional query to subset the results, as by
            default it will return all files in the given drive id. See the
            Google documentation for details of the syntax:
                https://developers.google.com/drive/api/v3/search-files
    """
    page_token = None
    files = []
    while True:
        results = (
            service.files()
            .list(
                corpora="drive",
                driveId=drive_id,
                includeItemsFromAllDrives=True,
                supportsAllDrives=True,
                q=query,
                pageSize=1000,
                fields="nextPageToken, files(id, name)",
            )
            .execute()
        )
        files.extend(results.get("files", []))
        page_token = results.get("nextPageToken", None)
        if page_token is None:
            break
    return files


def send_email_ses(
    subject, body_html, body_text, sender, recipients, identity_arn, charset="UTF-8"
):
    """
    Sends an email through AWS SES.

    Args:
        - subject (str): Email subject.
        - body_html (str): Email body with embedded HTML.
        - body_text (str): Fallback body to use when HTML can't be rendered.
        - sender (str): Email address of sender.
        - recipients (list): List of email recipients.
        - identity_arn (str): University of York identity ARN to authenticate
            through.
        - charset (str): Charset, defaults to UTF-8.

    Returns:
        None, sends email as a side-effect.
    """
    client = boto3.client("ses")
    try:
        client.send_email(
            Destination={"ToAddresses": recipients,},
            Message={
                "Body": {
                    "Html": {"Charset": charset, "Data": body_html,},
                    "Text": {"Charset": charset, "Data": body_text,},
                },
                "Subject": {"Charset": charset, "Data": subject,},
            },
            Source=sender,
            SourceArn=identity_arn,
            ReturnPath=sender,
            ReturnPathArn=identity_arn,
        )
    except ClientError as e:
        raise EmailSendingError


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
            raise SetupError(
                ("Log file {} already exists. " "Halting execution.").format(logfn)
            )
        file_logger = logging.FileHandler(logfn)
        file_logger.setFormatter(log_fmt)
        root_logger.addHandler(file_logger)


def parse_env_vars():
    """
    Parses environment variables.

    Variables are either passed in as environment variables (when run in
    production) or read in from a local file (when developing).
    The dotenv package handles reading the environment variables in from either
    source.

    The env vars are stored in JSON format, so this function splits them up into
    each keyword-value pair.

    Args:
        None

    Returns:
        None
    """

    load_dotenv()
    try:
        env_vars = parse_JSON_environment_variable("QUANT_CREDS")
    except SetupError:
        return False

    for k, v in env_vars.items():
        os.environ[k] = v

    return True
