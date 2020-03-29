from datetime import datetime
from string import Template
import csv
import requests as re
from bs4 import BeautifulSoup
from quantscraper.manufacturers.Manufacturer import Manufacturer
from quantscraper.utils import LoginError, DataDownloadError


class Aeroqual(Manufacturer):
    name = "Aeroqual"

    def __init__(self, cfg):
        """
        Sets up object with parameters needed to scrape data.

        Args:
            - cfg: Instance of ConfigParser

        Returns:
            None
        """
        self.auth_url = cfg.get(self.name, "auth_url")
        self.select_device_url = cfg.get(self.name, "select_device_url")
        self.data_url = cfg.get(self.name, "data_url")
        self.dl_url = cfg.get(self.name, "dl_url")
        self.device_ids = cfg.get(self.name, "devices").split(",")
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
        TODO
        """
        self.session = re.Session()
        try:
            result = self.session.post(
                self.auth_url, data=self.auth_params, headers=self.auth_headers
            )
            result.raise_for_status()
        except re.exceptions.HTTPError as ex:
            raise LoginError("HTTP error when logging in\n{}".format(ex)) from None

        # Check for authentication
        soup = BeautifulSoup(result.text, features="html.parser")
        login_div = soup.find(id="loginContent")
        if login_div is not None:
            self.session.close()
            raise LoginError("Login failed")

    def scrape_device(self, deviceID):
        """
        TODO
        """
        try:
            result = self.session.post(
                self.select_device_url,
                json=[self.select_device_string.substitute(device=deviceID)],
                headers=self.select_device_headers,
            )
            result.raise_for_status()
        except re.exceptions.HTTPError as ex:
            raise DataDownloadError("Cannot select device.\n{}".format(ex)) from None

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

        try:
            result = self.session.get(self.dl_url, headers=self.dl_headers)
            result.raise_for_status()
        except re.exceptions.HTTPError as ex:
            raise DataDownloadError("Cannot download data\n{}".format(ex)) from None

        return result.content

    def process_device(self, deviceID):
        """
        TODO
        """
        # TODO Can change this to use property getter?
        raw_data = self._raw_data[deviceID]
        # TODO See if still need this conversion when get data from website
        # directly rather than from pickle
        raw_data = raw_data.decode("utf-8")

        # TODO error handle if no raw lines
        raw_lines = raw_data.split("\r\n")
        # This data comes with a number of metadata rows that we don't need to
        # store
        raw_lines = raw_lines[self.lines_skip :]

        lines = csv.reader(raw_lines, delimiter=",")
        return [r for r in lines]
