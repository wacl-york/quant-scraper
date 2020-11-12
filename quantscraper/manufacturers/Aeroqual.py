"""
    quantscraper.manufacturers.Aeroqual.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Concrete implementation of Manufacturer, representing the Aeroqual air
    quality instrumentation device manufacturer.
"""

from datetime import datetime, time
from string import Template
import csv
import os
import requests as re
import pandas as pd
from quantscraper.manufacturers.Manufacturer import Manufacturer
from quantscraper.utils import LoginError, DataDownloadError, DataParseError


class Aeroqual(Manufacturer):
    """
    Inherits attributes and methods from Manufacturer along with providing
    implementations of:
        - connect()
        - scrape_device()
        - parse_to_csv()
    """

    name = "Aeroqual"

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
        self.auth_url = cfg["auth_url"]
        self.calibration_url = cfg["calibration_url"]
        self.data_url = cfg["data_url"]
        self.lines_skip = cfg["lines_skip"]

        # Authentication
        self.auth_params = {
            "UserName": os.environ["AEROQUAL_USER"],
            "Password": os.environ["AEROQUAL_PW"],
        }
        self.auth_headers = {
            "content-type": "application/x-www-form-urlencoded",
            "connnection": "keep-alive",
        }

        self.data_params = {
            "from": Template("${start}"),
            "to": Template("${end}"),
            "averagingperiod": cfg["averaging_window"],
            "includejournal": cfg["include_journal"],
        }

        super().__init__(cfg, fields)

    def connect(self):
        """
        Establishes an HTTP connection to the Aeroqual website.

        Logs in with username and password, then checks for success by parsing
        the resultant HTML page to see if the login prompt is still present,
        indicating a login failure.

        The instance attribute 'session' stores a handle to the connection,
        holding any generated cookies and the history of requests.

        Args:
            - None.

        Returns:
            None, although a handle to the connection is stored in the instance
            attribute 'session'.
        """
        self.session = re.Session()
        try:
            result = self.session.post(
                self.auth_url, data=self.auth_params, headers=self.auth_headers
            )
            result.raise_for_status()
        except re.exceptions.HTTPError as ex:
            raise LoginError("HTTP error when logging in\n{}".format(ex)) from None
        except re.exceptions.ConnectionError as ex:
            raise LoginError(
                "Connection error when logging in\n{}".format(ex)
            ) from None

    def log_device_status(self, device_id):
        """
        Scrapes information about a device's operating condition.

        Args:
            - device_id (str): The ID used by the website to refer to the
                device.

        Returns:
            A dict of keyword-value parameters.
        """
        params = {}
        url = self.calibration_url + f"/{device_id}"
        try:
            result = self.session.get(url)
            result.raise_for_status()
        except re.exceptions.HTTPError as ex:
            raise DataDownloadError(
                "Cannot open calibration page.\n{}".format(ex)
            ) from None
        except re.exceptions.ConnectionError as ex:
            raise DataDownloadError(
                "Connection error when opening calibration page.\n{}".format(ex)
            ) from None

        raw_params = result.json()
        params = raw_params["sensors"]

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

        url = self.data_url + f"/{device_id}"

        # Can't specify times for scraping window, just dates.
        # Will just convert datetime to date and doesn't matter too much since
        # Aeroqual treats limits as inclusive, so will scrape too much data
        # Needs to be in US format MM/DD/YYYY
        start_dt = datetime.combine(start, time.min)
        end_dt = datetime.combine(end, time.max)
        start_fmt = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
        end_fmt = end_dt.strftime("%Y-%m-%dT%H:%M:%S")
        this_params = self.data_params.copy()
        this_params["from"] = this_params["from"].substitute(start=start_fmt)
        this_params["to"] = this_params["to"].substitute(end=end_fmt)

        try:
            result = self.session.get(url, params=this_params)
            result.raise_for_status()
        except re.exceptions.HTTPError as ex:
            if result.status_code == re.codes["no_content"]:
                msg = "No data available for selected date range."
            else:
                msg = "Unable to generate data for selected date range."
            msg = msg + "\n" + str(ex)
            raise DataDownloadError(msg) from None
        except re.exceptions.ConnectionError as ex:
            raise DataDownloadError(
                "Connection error when generating data.\n{}".format(ex)
            ) from None

        raw = result.json()
        raw_data = raw["data"]

        return raw_data

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
        df = pd.DataFrame(raw_data)
        df_list = [df.columns.values.tolist()] + df.values.tolist()
        return df_list
