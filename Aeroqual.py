import sys
from datetime import datetime
import requests as re
from Manufacturer import Manufacturer
import csv


class Aeroqual(Manufacturer):
    @property
    def name(self):
        """
        Manufacturer name, as used as a section in the config file.
        """
        return "Aeroqual"

    def __init__(self, cfg):
        """
        Sets up object with parameters needed to scrape data.

        Args:
            - cfg: Instance of ConfigParser

        Returns:
            None
        """
        self.username = cfg.get(self.name, "Username")
        self.password = cfg.get(self.name, "Password")
        self.auth_url = cfg.get(self.name, "auth_url")
        self.select_device_url = cfg.get(self.name, "select_device_url")
        self.data_url = cfg.get(self.name, "data_url")
        self.dl_url = cfg.get(self.name, "dl_url")
        self.include_journal = cfg.get(self.name, "include_journal")
        self.avg_window = cfg.get(self.name, "averaging_window")
        self.device_ids = cfg.get(self.name, "devices").split(",")
        self.lines_skip = cfg.getint(self.name, "lines_skip")

        # Authentication
        self.auth_params = {
            "Username": self.username,
            "Password": self.password,
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
        self.select_device_string = "serialNumber={device},o=York University,dc=root"

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

        # Can't get any more granular with Aeroqual than date.
        # Convert these limits to dates then, doesn't matter as
        # Aeroqual treats limits as inclusive
        # Needs to be in US format MM/DD/YYYY
        start_date = start_datetime.strftime("%m/%d/%Y")
        end_date = end_datetime.strftime("%m/%d/%Y")

        self.data_params = {
            "Period": "{} to {}".format(start_date, end_date),
            "AvgMinutes": self.avg_window,
            "IncludeJournal": self.include_journal,
        }

        # Download data
        self.dl_headers = {"content-type": "text/csv"}

        super().__init__(cfg)

    def scrape_device(self, deviceID):
        """
        TODO
        """

        # TODO Multiple returns, not ideal

        result = self.session.post(
            self.select_device_url,
            json=[self.select_device_string.format(device=deviceID)],
            headers=self.select_device_headers,
        )
        if result.status_code != re.codes["ok"]:
            print("Error: cannot select device {}".format(deviceID))
            return None
        print("select instrument response: " + str(result))

        result = self.session.post(
            self.data_url, data=self.data_params, headers=self.data_headers
        )
        if result.status_code != re.codes["ok"]:
            if result.status_code == re.codes["no_content"]:
                print("No data available for selected date range.")
            else:
                print("Unable to generate data for selected date range.")
            return None

        print("generate data response: " + str(result))

        result = self.session.get(self.dl_url, headers=self.dl_headers)
        print("download data response: " + str(result))
        if result.status_code != re.codes["ok"]:
            print("Error: cannot download data")
            return None

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
