"""
    quantscraper.manufacturers.AURN.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Concrete implementation of Manufacturer, representing the UK's AURN
    web portal.
"""

from datetime import datetime, time
import requests as re
import pandas as pd
from quantscraper.manufacturers.Manufacturer import Manufacturer
from quantscraper.utils import DataDownloadError, DataParseError


class AURN(Manufacturer):
    """
    Inherits attributes and methods from Manufacturer along with providing
    implementations of:
        - connect()
        - scrape_device()
        - parse_to_csv()
    """

    name = "AURN"

    def __init__(self, cfg, fields):
        """
        Sets up object with parameters needed to scrape data.

        Args:
            - cfg (dict): Keyword-argument properties set in the Manufacturer's
                'properties' attribute.
            - fields (list): List of dicts detailing the measurands available
                for this manufacturer and their properties.

        Returns:
            None.
        """
        self.session = None
        self.api_url = cfg["api_url"]
        self.timeseries_ids = cfg["timeseries_ids"]

        super().__init__(cfg, fields)

    def connect(self):
        """
        Establishes an HTTP connection to the AURN API.

        Since the AURN API doesn't require any authentication, this method
        doesn't do anything except setup an instance attribute for an HTTP
        session, which stores a handle to the connection, holding any
        generated cookies and the history of requests.

        Args:
            - None.

        Returns:
            None, although a handle to the connection is stored in the instance
            attribute 'session'.
        """
        self.session = re.Session()

    def log_device_status(self, device_id):
        """
        Scrapes information about a device's operating condition.

        This method doesn't do anything for the AURN API and returns an empty
        dictionary.

        Args:
            - device_id (str): The ID used by the website to refer to the
                device.

        Returns:
            A dict of keyword-value parameters.
        """
        params = {}
        return params

    def scrape_device(self, device_id, start, end):
        """
        Downloads the data for a given device.

        Args:
            - device_id (str): The ID used by the website to refer to the
                device.
            - start (date): The start of the scraping window.
            - end (date): The end of the scraping window.

        Returns:
            The raw data in JSON format, with each pollutant having its own
            object in the top-level object.
        """
        start_dt = datetime.combine(start, time.min)
        end_dt = datetime.combine(end, time.max)
        start_fmt = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_fmt = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        params = {
            "timespan": "{}/{}".format(start_fmt, end_fmt),
            "timeseries": self.timeseries_ids,
        }
        headers = {"Content-Type": "application/json", "Accept": "application/json"}

        try:
            result = self.session.post(self.api_url, json=params, headers=headers)
            result.raise_for_status()
        except re.exceptions.HTTPError as ex:
            raise DataDownloadError("Cannot download data.\n{}".format(ex)) from None
        except re.exceptions.ConnectionError as ex:
            raise DataDownloadError(
                "Connection error when downloading data.\n{}".format(ex)
            ) from None
        raw = result.json()

        return raw

    def parse_to_csv(self, raw_data):
        """
        Parses the raw data into a 2D list format.

        The raw data is stored in a JSON format with one object per sensor,
        containing timestamps and recordings.
        To get a single data structure representing this device (or station),
        these sensor-specific streams need to combined.
        Since we can't guarantee the timestamps will be identical across the
        sensors, each stream is loaded into a long pandas DataFrame which are
        then vertically stacked together.
        The overall CSV is formed by pivoting this into a wide DataFrame, before
        being converted into a 2D list.

        Args:
            - raw_data (str): A string containing the raw data in JSON format.

        Returns:
            A 2D list representing the data in a tabular format, so that each
            row corresponds to a unique time-point and each column holds a
            measurand.
        """
        # Turn list of dicts from raw data into list of long pandas DataFrames
        dfs = []
        for field_id in raw_data.keys():
            try:
                df = pd.DataFrame(raw_data[field_id]["values"])
            except (pd.errors.EmptyDataError, KeyError):
                continue
            # Filter to rows which have timestamp, otherwise can't
            # pivot later as well have duplicate keys (i.e. NaN timestamp)
            try:
                df = df[df.timestamp.notnull()]
            except AttributeError:
                continue

            if len(df) == 0:
                continue

            df["field"] = field_id
            dfs.append(df)

        if len(dfs) == 0:
            return []

        long_combined = pd.concat(dfs)
        # Convert timestamp from Unix into ISO8061
        long_combined["timestamp"] = pd.to_datetime(
            long_combined["timestamp"], unit="ms", errors="coerce"
        )
        # Filter to rows which have valid timestamp, otherwise can't
        # pivot later as well have duplicate keys (i.e. NaN timestamp)
        try:
            long_combined = long_combined[long_combined.timestamp.notnull()]
        except AttributeError:
            return []

        # Cast to wide and then form into 2D list
        try:
            wide = long_combined.pivot(
                index="timestamp", columns="field", values="value"
            ).reset_index()
        except ValueError:
            raise DataParseError("Could not convert long column to wide")
        wide["timestamp"] = wide["timestamp"].dt.strftime(self.timestamp_format)
        wide_list = [wide.columns.tolist()] + wide.values.tolist()

        return wide_list
