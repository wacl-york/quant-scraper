"""
    quantscraper.manufacturers.Bosch.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Concrete implementation of Manufacturer, representing the Bosch air
    quality instrumentation device manufacturer.
"""

from datetime import datetime, time
import json
import os
import requests as re
import pandas as pd
from quantscraper.manufacturers.Manufacturer import Manufacturer
from quantscraper.utils import LoginError, DataDownloadError


class Bosch(Manufacturer):
    """
    Inherits attributes and methods from Manufacturer along with providing
    implementations of:
        - connect()
        - scrape_device()
        - parse_to_csv()
    """

    name = "Bosch"

    def __init__(self, cfg, fields):
        """
        Sets up object with parameters needed to scrape data.

        Args:
            - cfg (dict): Keyword-argument properties set in the Manufacturer's
                'properties' attribute.
            - fields (list): List of dicts detailing the measurands available
                for this manufacturer and their properties.

        Returns:
            None
        """
        self.session = None
        self.username = os.environ["BOSCH_USER"]
        self.password = os.environ["BOSCH_PW"]
        self.base_url = cfg["base_url"]
        self.project_id = cfg["project_id"]
        self.query_id_status = cfg["query_id_3.1"]
        self.query_id_data = cfg["query_id_3.5"]

        self.header = {"Content-Type": "application/json", "Accept": "application/json"}

        super().__init__(cfg, fields)

    def connect(self):
        """
        Does nothing for Bosch as Basic Authorization is used (base64 encoding
        of username:password in every request header), beyond creating a session
        instance attribute.

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

        Args:
            - device_id (str): The ID used by the website to refer to the
                device.

        Returns:
            A dict of keyword-value parameters.
        """
        url_to_call = f"{self.base_url}/{self.project_id}/query-templates/{self.query_id_status}/execute-query"
        params = {
            "parameterValues": {"Type": "INIT", "deviceID": device_id},
            "queryTag": "string",
            "tag": None,
        }

        try:
            result = self.session.post(
                url_to_call,
                json=params,
                auth=(self.username, self.password),
                headers=self.header,
            )
            result.raise_for_status()
        except re.exceptions.HTTPError as ex:
            raise DataDownloadError(
                "Cannot get device status.\n{}".format(str(ex))
            ) from None
        except re.exceptions.ConnectionError as ex:
            raise DataDownloadError(
                "Connection error when getting device status.\n{}".format(str(ex))
            ) from None

        raw = result.json()
        params = raw[0]["payload"]
        return params

    def scrape_device(self, device_id, start, end):
        """
        Downloads the data for a given device from the API.

        This just requires a single API GET request with the appropriate params.

        Args:
            - device_id (str): The ID used by the website to refer to the
                device.
            - start (date): The start of the scraping window.
            - end (date): The end of the scraping window.

        Returns:
            The data is returned as a list of objects representing each
            timepoint. These objects have a single attribute "payload" 
            containing a further object containing measurements in keyword-value
            pair format.
        """
        # Convert start and end times into required format of
        # YYYY-mm-ddTHH:mm:ss.fffZ
        # Bosch API uses [closed, open] intervals
        start_dt = datetime.combine(start, time.min)
        end_dt = datetime.combine(end, time.max)
        start_fmt = start_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")
        end_fmt = end_dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")

        url_to_call = f"{self.base_url}/{self.project_id}/query-templates/{self.query_id_data}/execute-query"
        params = {
            "parameterValues": {
                "Type": "DATA",
                "deviceID": device_id,
                "TimestampRange": {"from": start_fmt, "to": end_fmt},
            },
            "queryTag": "string",
            "tag": None,
        }
        try:
            result = self.session.post(
                url_to_call,
                json=params,
                auth=(self.username, self.password),
                headers=self.header,
            )
            result.raise_for_status()
        except re.exceptions.HTTPError as ex:
            raise DataDownloadError(
                "Cannot download data.\n{}".format(str(ex))
            ) from None
        except re.exceptions.ConnectionError as ex:
            raise DataDownloadError(
                "Connection error when downloading data.\n{}".format(str(ex))
            ) from None

        try:
            data = result.json()
        except (json.decoder.JSONDecodeError, TypeError):
            raise DataDownloadError("No 'Data' attribute in downloaded json.") from None

        return data

    def parse_to_csv(self, raw_data):
        """
        Parses the raw data into a 2D list format.

        Since the raw data is already in a hierarchical format, it is easier to
        read it into Pandas, rather than do this manually in base Python.

        Args:
            - raw_data (dict): The data is returned as a list of objects 
                representing each timepoint. These objects have a single 
                attribute "payload" containing a further object containing 
                measurements in keyword-value pair format.

        Returns:
            A 2D list representing the data in a tabular format, so that each
            row corresponds to a unique time-point and each column holds a
            measurand.
        """
        measurements = [x["payload"] for x in raw_data]
        df = pd.DataFrame(measurements)
        df_list = [df.columns.tolist()] + df.values.tolist()

        return df_list
