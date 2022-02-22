"""
    quantscraper.manufacturers.Oizom.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Concrete implementation of Manufacturer, representing the Oizom air
    quality instrumentation device manufacturer.
"""

from datetime import datetime, time, timezone
import json
import os
from time import sleep
import requests as re
import pandas as pd
from quantscraper.manufacturers.Manufacturer import Manufacturer
from quantscraper.utils import LoginError, DataDownloadError, DataParseError


class Oizom(Manufacturer):
    """
    Inherits attributes and methods from Manufacturer along with providing
    implementations of:
        - connect()
        - scrape_device()
        - parse_to_csv()
    """

    name = "Oizom"

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
        self.base_url = cfg["base_url"]
        self.client_id = os.environ["OIZOM_ID"]
        self.client_secret = os.environ["OIZOM_SECRET"]
        self.average = cfg["average_seconds"]

        super().__init__(cfg, fields)

    def connect(self):
        """
        Generates an API access token from the user credentials.

        Args:
            - None.

        Returns:
            None, although a handle to the connection is stored in the instance
            attribute 'session' and the header needed to authorize future
            requests is stored in the instance attribute 'auth_headers'.
        """
        url_to_call = f"{self.base_url}/v1/oauth2/token"

        params = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "grant_type": "client_credentials",
            "scope": "view_data",
        }

        self.session = re.Session()
        try:
            result = self.session.post(url_to_call, data=params)
            result.raise_for_status()
        except re.exceptions.HTTPError as ex:
            raise LoginError(
                "Cannot obtain access token.\n{}".format(str(ex))
            ) from None
        except re.exceptions.ConnectionError as ex:
            raise LoginError(
                "Connection error when obtaining access token.\n{}".format(str(ex))
            ) from None

        res = result.json()
        access_token = res["access_token"]

        self.auth_header = {
            "Authorization": f"Bearer {access_token}",
            "ClientId": self.client_id,
            "Content-Type": "application/json",
        }

    def log_device_status(self, device_id):
        """
        Scrapes information about a device's operating condition.

        Args:
            - device_id (str): The ID used by the website to refer to the
                device.

        Returns:
            A dict of keyword-value parameters.
        """
        url_to_call = f"{self.base_url}/v1/devices/{device_id}"
        try:
            result = self.session.get(url_to_call, headers=self.auth_header)
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
            params1 = result.json()
        except (json.decoder.JSONDecodeError, TypeError):
            raise DataDownloadError("No 'Data' attribute in downloaded json.") from None

        url_to_call = f"{self.base_url}/v1/devices/{device_id}/status"
        try:
            result = self.session.get(url_to_call, headers=self.auth_header)
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
            params2 = result.json()
        except (json.decoder.JSONDecodeError, TypeError):
            raise DataDownloadError("No 'Data' attribute in downloaded json.") from None

        params1.update(params2)

        # Oizom rate limits to 4 calls a second
        sleep(1)

        return params1

    def scrape_device(self, device_id, start, end):
        """
        Downloads the data for a given device from the API.

        Args:
            - device_id (str): The ID used by the website to refer to the
                device.
            - start (date): The start of the scraping window.
            - end (date): The end of the scraping window.

        Returns:
            The data is stored as a list of dicts, corresponding to each
            time-sample. Each object contains a 'payload' object which has a
            single object 'd' which is what contains the measurements in
            key-value pairs.
        """
        # Convert start and end times into required POSIX format
        # Oizom API uses [closed, closed] intervals
        start_dt = datetime.combine(start, time.min)
        end_dt = datetime.combine(end, time.max)
        start_fmt = round(start_dt.replace(tzinfo=timezone.utc).timestamp())
        end_fmt = round(end_dt.replace(tzinfo=timezone.utc).timestamp())

        params = {"gte": start_fmt, "lte": end_fmt, "avg": self.average}

        url_to_call = f"{self.base_url}/v1/data/analytics/{device_id}"
        try:
            result = self.session.get(
                url_to_call, headers=self.auth_header, params=params
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

        # Oizom rate limits to 4 calls a second
        sleep(1)

        return data

    def parse_to_csv(self, raw_data):
        """
        Parses the raw data into a 2D list format.

        Since the raw data is already in a hierarchical format, it is easier to
        read it into Pandas, rather than do this manually in base Python.

        Args:
            - raw_data (dict): The data is stored as a list of dicts,
            corresponding to each time-sample. Each object contains a 'payload'
            object which has a single object 'd' which is what contains the
            measurements in key-value pairs.

        Returns:
            A 2D list representing the data in a tabular format, so that each
            row corresponds to a unique time-point and each column holds a
            measurand.
        """
        try:
            measurements = [x["payload"]["d"] for x in raw_data]
        except KeyError:
            raise DataParseError(
                "Expected fields 'payload' and 'd' not present in raw data."
            )

        df = pd.DataFrame(measurements)
        # timestamp is in POSIX format
        try:
            df["t"] = pd.to_datetime(df["t"], unit="s")
        except KeyError:
            raise DataParseError("Field 't' not present in measurements data.")

        df["t"] = df["t"].dt.strftime("%Y-%m-%d %H:%M:%S")
        df_list = [df.columns.tolist()] + df.values.tolist()

        return df_list
