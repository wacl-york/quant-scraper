"""
    quantscraper.manufacturers.Aeroqual.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Concrete implementation of Manufacturer, representing the Aeroqual air
    quality instrumentation device manufacturer.
"""

from datetime import datetime
from string import Template
import csv
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

    def __init__(self, cfg):
        """
        Sets up object with parameters needed to scrape data.

        Args:
            - cfg (configparser.Namespace): Instance of ConfigParser.

        Returns:
            None.
        """
        self.session = None
        self.auth_url = cfg.get(self.name, "auth_url")
        self.select_device_url = cfg.get(self.name, "select_device_url")
        self.data_url = cfg.get(self.name, "data_url")
        self.dl_url = cfg.get(self.name, "dl_url")
        self.lines_skip = cfg.getint(self.name, "lines_skip")

        # Authentication
        self.auth_params = {
            "Username": cfg.get(self.name, "Username"),
            "Password": cfg.get(self.name, "Password"),
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

        # Load start and end scraping datetimes
        start_datetime = cfg.get("Main", "start_time")
        start_datetime = datetime.fromisoformat(start_datetime)
        end_datetime = cfg.get("Main", "end_time")
        end_datetime = datetime.fromisoformat(end_datetime)

        # Can't specify times for scraping window, just dates.
        # Will just convert datetime to date and doesn't matter too much since
        # Aeroqual treats limits as inclusive, so will scrape too much data
        # Needs to be in US format MM/DD/YYYY
        start_date = start_datetime.strftime("%m/%d/%Y")
        end_date = end_datetime.strftime("%m/%d/%Y")

        self.data_params = {
            "Period": "{} to {}".format(start_date, end_date),
            "AvgMinutes": cfg.get(self.name, "averaging_window"),
            "IncludeJournal": cfg.get(self.name, "include_journal"),
        }

        # Download data
        self.dl_headers = {"content-type": "text/csv"}

        super().__init__(cfg)

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

    def scrape_device(self, device_id):
        """
        Downloads the data for a given device from the website.

        This process requires several HTTP requests to be made:
            - A POST call to select the device
            - A POST call to generate the data for a given time-frame
            - A GET call to obtain the data.

        Args:
            device_id (str): The website device_id to scrape for.

        Returns:
            A string containing the raw data in CSV format, i.e. rows are
            delimited by '\r\n' characters and columns by ','.
        """
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
                self.data_url, data=self.data_params, headers=self.data_headers
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
