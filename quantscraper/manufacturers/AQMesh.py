"""
    quantscraper.manufacturers.AQMesh.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Concrete implementation of Manufacturer, representing the AQMesh air
    quality instrumentation device manufacturer.
"""

from string import Template
from datetime import datetime
import json
import requests as re
from bs4 import BeautifulSoup
from quantscraper.manufacturers.Manufacturer import Manufacturer
from quantscraper.utils import LoginError, DataDownloadError, DataParseError


class AQMesh(Manufacturer):
    """
    Inherits attributes and methods from Manufacturer along with providing
    implementations of:
        - connect()
        - scrape_device()
        - parse_to_csv()
    """

    name = "AQMesh"

    def __init__(self, cfg):
        """
        Sets up object with parameters needed to scrape data.

        Args:
            - cfg (configparser.Namespace): Instance of ConfigParser.

        Returns:
            None
        """
        self.session = None
        self.auth_url = cfg.get(self.name, "auth_url")
        self.data_url = cfg.get(self.name, "data_url")

        # Authentication
        self.auth_params = {
            "username": cfg.get(self.name, "Username"),
            "password": cfg.get(self.name, "Password"),
        }
        self.auth_headers = {"referer": cfg.get(self.name, "auth_referer")}

        # Download data
        self.data_headers = {
            "content-type": "application/json; charset=UTF-8",
            "referer": cfg.get(self.name, "data_referer"),
        }

        # Convert start and end times into required format of
        # YYYY-mm-ddTHH:mm:ss TZ:TZ
        # Where TZ:TZ is in HH:MM format
        # Making assumption here that have no timezone!
        timezone = cfg.get(self.name, "timezone")
        start_str = cfg.get("Main", "start_time")
        end_str = cfg.get("Main", "end_time")
        start_dt = datetime.fromisoformat(start_str)
        end_dt = datetime.fromisoformat(end_str)
        start_fmt = start_dt.strftime("%Y-%m-%dT%H:%M:%S {}".format(timezone))
        end_fmt = end_dt.strftime("%Y-%m-%dT%H:%M:%S {}".format(timezone))

        self.data_params = {
            "CRUD": "READ",
            "Call": "telemetrytable",
            "UniqueId": Template("${device}"),
            "Channels": Template(
                "${device}-AIRPRES-0+${device}-CO2-0+${device}-HUM-0+${device}-NO-0+${device}-NO2-0+${device}-O3-0+${device}-PARTICLE_COUNT-0+${device}-PM1-0+${device}-PM10-0+${device}-PM2.5-0+${device}-PM4-0+${device}-TEMP-0+${device}-TSP-0+${device}-VOLTAGE-0"
            ),
            "Start": start_fmt,
            "End": end_fmt,
            "TimeZone": timezone,
            "Average": cfg.get(self.name, "averaging_window"),
            "TimeConvention": "timebeginning",
            "Units": cfg.get(self.name, "units"),
            "DataType": cfg.get(self.name, "data_type"),
            "ReadingMinValue": "",
            "ReadingMaxValue": "",
            "Assignment": "current",
            "ShowFlags": "true",
            "ShowScaling": "true",
            "AdditionalParameters": "",
        }

        super().__init__(cfg)

    def connect(self):
        """
        Establishes an HTTP connection to the AQMesh website.

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

        # Check for authentication
        soup = BeautifulSoup(result.text, features="html.parser")
        login_div = soup.find(id="loginBox")
        if login_div is not None:
            self.session.close()
            raise LoginError("Login failed")

    def scrape_device(self, device_id):
        """
        Downloads the data for a given device from the website.

        This just requires a single GET request with the appropriate params.
        The raw data is held in the 'Data' attribute of the response JSON.

        Args:
            device_id (str): The website device_id to scrape for.

        Returns:
            The data stored in a hierarchical format comprising dicts and lists.
            At the top level, the data has 2 attributes, 'Headers' and 'Rows',
            which hold the column labels and data respectively.
        """
        this_params = self.data_params.copy()
        this_params["UniqueId"] = this_params["UniqueId"].substitute(device=device_id)
        this_params["Channels"] = this_params["Channels"].substitute(device=device_id)

        try:
            result = self.session.get(
                self.data_url, params=this_params, headers=self.data_headers,
            )
            result.raise_for_status()
        except re.exceptions.HTTPError as ex:
            raise DataDownloadError(
                "Cannot download data.\n{}".format(str(ex))
            ) from None

        try:
            data = result.json()["Data"]
        except (json.decoder.JSONDecodeError, TypeError):
            raise DataDownloadError("No 'Data' attribute in downloaded json.") from None

        return data

    def parse_to_csv(self, raw_data):
        """
        Parses the raw data into a 2D list format.

        Args:
            - raw_data (dict): The data is stored in a hierarchical format
                comprising dicts and lists. At the top level, the data has
                2 attributes, 'Headers' and 'Rows', which hold the column
                labels and data respectively.

        Returns:
            A 2D list representing the data in a tabular format, so that each
            row corresponds to a unique time-point and each column holds a
            measurand.
        """
        # Combine header and data into 1 list
        header = [h["Header"] for h in raw_data["Headers"]]
        clean_data = raw_data["Rows"]

        # Check have consistent number of columns
        ncols = [len(row) for row in clean_data]
        if len(set(ncols)) > 1:
            raise DataParseError("Have differing number of columns: {}".format(ncols))

        if ncols[0] != len(header):
            raise DataParseError(
                "Have differing number of columns ({}) to headers ({})".format(
                    ncols[0], len(header)
                )
            )

        clean_data.insert(0, header)

        return clean_data
