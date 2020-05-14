"""
    quantscraper.manufacturers.Aeroqual.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Concrete implementation of Manufacturer, representing the Aeroqual air
    quality instrumentation device manufacturer.
"""

from datetime import date
from string import Template
import csv
import os
import requests as re
from bs4 import BeautifulSoup
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
        self.select_device_url = cfg["select_device_url"]
        self.data_url = cfg["data_url"]
        self.dl_url = cfg["dl_url"]
        self.lines_skip = cfg["lines_skip"]

        # Authentication
        self.auth_params = {
            "Username": os.environ["AEROQUAL_USER"],
            "Password": os.environ["AEROQUAL_PW"],
            "RememberMe": "true",
        }
        self.auth_headers = {
            "content-type": "application/x-www-form-urlencoded",
            "connnection": "keep-alive",
            "referer": self.auth_url,
        }

        # Select device
        self.select_device_headers = {
            "connection": "keep-alive",
            "content-type": "application/json",
        }
        self.select_device_string = Template(
            "serialNumber=${device},o=York University,dc=root"
        )

        # Generate data
        self.data_headers = {
            "content-type": "application/x-www-form-urlencoded;charset=UTF-8",
            "connection": "keep-alive",
        }

        self.data_params = {
            "Period": Template("${start} to ${end}"),
            "AvgMinutes": cfg["averaging_window"],
            "IncludeJournal": cfg["include_journal"],
        }

        # Download data
        self.dl_headers = {"content-type": "text/csv"}

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

        # Check for authentication
        soup = BeautifulSoup(result.text, features="html.parser")
        login_div = soup.find(id="loginContent")
        if login_div is not None:
            self.session.close()
            raise LoginError("Login failed")

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
            - start (datetime): The start of the scraping window.
            - end (datetime): The end of the scraping window.

        Returns:
            A string containing the raw data in CSV format, i.e. rows are
            delimited by '\r\n' characters and columns by ','.
        """
        # Can't specify times for scraping window, just dates.
        # Will just convert datetime to date and doesn't matter too much since
        # Aeroqual treats limits as inclusive, so will scrape too much data
        # Needs to be in US format MM/DD/YYYY
        start_fmt = start.strftime("%m/%d/%Y")
        end_fmt = end.strftime("%m/%d/%Y")
        this_params = self.data_params.copy()
        this_params["Period"] = this_params["Period"].substitute(
            start=start_fmt, end=end_fmt
        )
        try:
            result = self.session.post(
                self.select_device_url,
                json=[self.select_device_string.substitute(device=device_id)],
                headers=self.select_device_headers,
            )
            result.raise_for_status()
        except re.exceptions.HTTPError as ex:
            raise DataDownloadError("Cannot select device.\n{}".format(ex)) from None
        except re.exceptions.ConnectionError as ex:
            raise DataDownloadError(
                "Connection error when selecting device.\n{}".format(ex)
            ) from None

        try:
            result = self.session.post(
                self.data_url, data=this_params, headers=self.data_headers
            )
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

        try:
            result = self.session.get(self.dl_url, headers=self.dl_headers)
            result.raise_for_status()
        except re.exceptions.HTTPError as ex:
            raise DataDownloadError("Cannot download data\n{}".format(ex)) from None
        except re.exceptions.ConnectionError as ex:
            raise DataDownloadError(
                "Connection error when downloading data.\n{}".format(ex)
            ) from None

        raw = result.text
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
        # Expect to get an empty row at the end due to suplerfuous carriage
        # return. Remove any trailing white-space (including CR).
        # rstrip() won't raise error if no trailing white-space
        raw_data = raw_data.rstrip()

        # Split into rows and run basic validation
        raw_lines = raw_data.split("\r\n")

        if len(raw_lines) < self.lines_skip:
            raise DataParseError(
                "Fewer lines ({}) available than expected number of headers ({})".format(
                    len(raw_lines), self.lines_skip
                )
            )

        header_removed = raw_lines[self.lines_skip :]
        if len(header_removed) == 0:
            raise DataParseError("Have no rows of data available.")

        # Parse into CSV. reader returns generator so turn into list
        data = csv.reader(header_removed, delimiter=",")
        data = [row for row in data]

        # Check have consistent number of columns.
        # Only test have > 1 column as unsure what would be expected number, but
        # can be fairly sure that just 1 column is a sign something's gone wrong
        ncols = [len(row) for row in data]
        unique_ncols = set(ncols)
        if len(unique_ncols) > 1:
            raise DataParseError(
                "Rows have differing number of columns: {}.".format(unique_ncols)
            )
        if ncols[0] == 1:
            raise DataParseError("Rows only have 1 column.")

        return data
