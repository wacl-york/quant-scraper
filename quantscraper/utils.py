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
    Custom exception class for situations where a parse into CSV has failed.
    """
