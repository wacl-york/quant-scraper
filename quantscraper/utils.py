"""
    utils.py
    ~~~~~~~~

    Contains utility functions.
"""

import pickle

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
