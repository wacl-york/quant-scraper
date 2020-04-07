"""
    utils.py
    ~~~~~~~~

    Contains utility functions.
"""

import os
import pickle

from google.oauth2 import service_account
import googleapiclient.discovery
from googleapiclient.http import MediaFileUpload


class LoginError(Exception):
    """
    Custom exception class for situations where a login attempt has failed.
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


class ValidateDataError(Exception):
    """
    Custom exception class for situations where saving a file has failed.
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
    n_clean = counts['timestamp']
    try:
        pct_clean = n_clean / n_raw * 100
    except ZeroDivisionError:
        pct_clean = 0

    summary = "Found {}/{} ({:.1f}%) rows with usable timestamps. Data fields: ".format(n_clean, n_raw, pct_clean)

    for measurand, measurand_clean in counts.items():
        if measurand == 'timestamp':
            continue
        try:
            pct_clean = measurand_clean / n_clean * 100
        except ZeroDivisionError:
            pct_clean = 0

        measurand_str = "{} {}/{} ({:.1f}%)\t".format(measurand, measurand_clean,
                                                      n_clean,
                                                      pct_clean)
        summary += measurand_str
    return summary

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
    scopes = ['https://www.googleapis.com/auth/drive']
    SERVICE_ACCOUNT_FILE = credentials_fn

    credentials = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=scopes)
    service = googleapiclient.discovery.build('drive', 'v3', credentials=credentials)
    return service


def upload_file_google_drive(service, fn, folder_id, mime_type='text/csv'):
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
    # TODO:
    #    - Implement resumable upload
    #    - Sort permissions for writer to only access Data folder

    # Filename should be base filename, removing path
    base_fn = os.path.basename(fn)

    file_metadata = {
        'name': base_fn,
        'mimeType': mime_type,
        'parents': [folder_id]
    }

    media = MediaFileUpload(fn,
                            mimetype=mime_type,
                            resumable=True)

    service.files().create(body=file_metadata,
                           media_body=media,
                           supportsAllDrives=True).execute()

