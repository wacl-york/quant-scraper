import sys
from datetime import datetime
from string import Template
import requests as re
from Manufacturer import Manufacturer


class Zephyr(Manufacturer):
    @property
    def name(self):
        """
        Manufacturer name, as used as a section in the config file.
        """
        return "Zephyr"

    @property
    def clean_data(self):
        """
        TODO
        """
        pass

    def __init__(self, cfg):
        """
        Sets up object with parameters needed to scrape data.

        Args:
            - cfg: Instance of ConfigParser

        Returns:
            None
        """
        self.username = cfg.get(self.name, "username")
        self.password = cfg.get(self.name, "password")
        self.auth_url = cfg.get(self.name, "auth_url")
        self.auth_referer = cfg.get(self.name, "auth_referer")
        self.device_ids = cfg.get(self.name, "devices").split(",")

        # Authentication
        self.auth_params = {
            "username": self.username,
            "password": self.password,
            "grant_type": "password",
        }
        self.auth_headers = {"referer": self.auth_referer}

        # Download data
        self.data_headers = {"content-type": "application/json; charset=UTF-8"}

        # Load start and end scraping datetimes
        start_datetime = cfg.get("Main", "start_time")
        end_datetime = cfg.get("Main", "end_time")
        start_date = datetime.fromisoformat(start_datetime).strftime("%Y%m%d%H%M%S")
        end_date = datetime.fromisoformat(end_datetime).strftime("%Y%m%d%H%M%S")

        self.start_date = start_date
        self.end_date = end_date

        # TODO Debug and see if these parameters (AB/newDef/6) are hardcoded
        raw_data_url = cfg.get(self.name, "data_url")
        self.data_url = Template(
            raw_data_url + "/$token/$device/$start/$end/AB/newDef/6/JSON/api"
        )

        super().__init__(cfg)

    def connect(self):
        """
        Overrides super method as needs to obtain API token
        """
        self.session = re.Session()
        result = self.session.post(
            self.auth_url, data=self.auth_params, headers=self.auth_headers
        )
        print("auth response: " + str(result))

        if result.status_code != re.codes["ok"]:
            # TODO convert to log
            print("Error: cannot connect")
            return False
        else:
            self.api_token = result.json()["access_token"]
            return True

    def scrape_device(self, deviceID):
        """
        TODO
        """
        # TODO Replace ALL format calls with substitute where allowing user
        # input
        this_url = self.data_url.substitute(
            device=deviceID,
            token=self.api_token,
            start=self.start_date,
            end=self.end_date,
        )
        # TODO Multiple returns, not ideal
        result = self.session.get(this_url, headers=self.data_headers,)
        if result.status_code != re.codes["ok"]:
            print("Error: cannot download data")
            return None
        data = result.json()

        return data
