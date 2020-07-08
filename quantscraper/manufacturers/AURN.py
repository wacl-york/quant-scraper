"""
    quantscraper.manufacturers.AURN.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Concrete implementation of Manufacturer, representing the UK's AURN
    web portal.
"""

from string import Template
from datetime import datetime, timedelta, time
import csv
import os
import requests as re
from bs4 import BeautifulSoup
import pandas as pd
from quantscraper.manufacturers.Manufacturer import Manufacturer
from quantscraper.utils import LoginError, DataDownloadError, DataParseError


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

        The instance attribute 'session' stores a handle to the connection,
        holding any generated cookies and the history of requests.

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

        Abstract method that must have a concrete implementation provided by
        sub-classes.

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
        Downloads the data for a given device from the website.

        This process requires several HTTP requests to be made:
            - A POST call to select the device
            - A POST call to generate the data for a given time-frame
            - A GET call to obtain the data.

        Args:
            - device_id (str): The ID used by the website to refer to the
                device.
            - start (date): The start of the scraping window.
            - end (date): The end of the scraping window.

        Returns:
            A string containing the raw data in CSV format, i.e. rows are
            delimited by '\r\n' characters and columns by ','.
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
            raise DataDownloadError("Cannot select device.\n{}".format(ex)) from None
        except re.exceptions.ConnectionError as ex:
            raise DataDownloadError(
                "Connection error when selecting device.\n{}".format(ex)
            ) from None
        raw = result.json()

        return raw

    def parse_to_csv(self, raw_data):
        """
        Parses the raw data into a 2D list format.

        The raw data is already in CSV format, so it simply needs delimiting by
        carriage return to get the rows, and then separating columns by commas.

        Args:
            - raw_data (str): A string containing the raw data in CSV format,
                i.e. rows are delimited by '\r\n' characters and columns by ','.

        Returns:
            A 2D list representing the data in a tabular format, so that each
            row corresponds to a unique time-point and each column holds a
            measurand.
        """
        data = raw_data

        # Turn list of dicts from raw data into list of long pandas DataFrames
        dfs = []
        for field_id in raw_data.keys():
            try:
                df = pd.DataFrame(raw_data[field_id]["values"])
            except pd.errors.EmptyDataError:
                continue
            df["field"] = field_id
            dfs.append(df)
        long_combined = pd.concat(dfs)
        # Convert timestamp from Unix into ISO8061
        long_combined["timestamp"] = pd.to_datetime(
            long_combined["timestamp"], unit="ms"
        )

        # Cast to wide and then form into 2D list
        try:
            wide = long_combined.pivot(
                index="timestamp", columns="field", values="value"
            ).reset_index()
        except ValueError:
            raise DataParseError("Could not convert long column to wide")
        wide["timestamp"] = wide["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")
        wide_list = [wide.columns.tolist()] + wide.values.tolist()

        return wide_list
