"""
    utils.py
    ~~~~~~~~

    Contains utility functions.
"""


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
