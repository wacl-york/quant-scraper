"""
    quantscraper.manufacturers.Kunak.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Concrete implementation of Manufacturer, representing the Kunak air
    quality instrumentation device manufacturer.
"""

from datetime import datetime, time, timezone
import json
import os
import requests as re
import pandas as pd
from quantscraper.manufacturers.Manufacturer import Manufacturer
from quantscraper.utils import LoginError, DataDownloadError, DataParseError


class Kunak(Manufacturer):
    """
    Inherits attributes and methods from Manufacturer along with providing
    implementations of:
        - connect()
        - scrape_device()
        - parse_to_csv()
    """

    name = "Kunak"

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
        self.username = os.environ["KUNAK_USER"]
        self.password = os.environ["KUNAK_PW"]

        super().__init__(cfg, fields)
        self.fields_to_scrape = [x["webid"] for x in self.measurands]

    def connect(self):
        """
        Verifies that the supplied credentials work.

        The instance attribute 'session' stores a handle to the connection,
        holding any generated cookies and the history of requests.

        Args:
            - None.

        Returns:
            None, although a handle to the connection is stored in the instance
            attribute 'session'.
        """
        self.session = re.Session()
        url_to_call = (
            f"https://kunakcloud.com/openAPIv0/v1/rest/users/{self.username}/info"
        )

        try:
            result = self.session.get(url_to_call, auth=(self.username, self.password))
            result.raise_for_status()
        except re.exceptions.HTTPError as ex:
            if result.status_code == 401:
                msg = "Authentication error, check credentials"
            else:
                msg = "Error when authenticating"
            raise LoginError(f"{msg}.\n{str(ex)}") from None
        except re.exceptions.ConnectionError as ex:
            raise LoginError(
                "Connection error when testing authentication.\n{}".format(str(ex))
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
        url_to_call = (
            f"https://kunakcloud.com/openAPIv0/v1/rest/devices/{device_id}/info"
        )
        try:
            result = self.session.get(url_to_call, auth=(self.username, self.password))
            result.raise_for_status()
        except re.exceptions.HTTPError as ex:
            raise DataDownloadError(
                f"HTTP error when logging device status.\n{str(ex)}"
            ) from None
        except re.exceptions.ConnectionError as ex:
            raise DataDownloadError(
                f"Connection error when logging device status.\n{str(ex)}"
            ) from None

        params = result.json()

        return params

    def scrape_device(self, device_id, start, end):
        """
        Downloads the data for a given device from the website.

        This just requires a single API GET request with the appropriate params.
        The raw data is held in the 'Data' attribute of the response JSON.

        Args:
            - device_id (str): The ID used by the website to refer to the
                device.
            - start (date): The start of the scraping window.
            - end (date): The end of the scraping window.

        Returns:
            The data stored as a list of objects, with each object containing
            the keys ["ts", "sensor_tag", and "value"] giving the timestamp,
            measurand key, and measurement respectively.
            The objects also contain validation flags.
        """
        # Convert start and end times into required POSIX format (in ms)
        # Kunak API uses [closed, open] intervals
        start_dt = datetime.combine(start, time.min)
        end_dt = datetime.combine(end, time.max)
        start_fmt = start_dt.replace(tzinfo=timezone.utc).timestamp() * 1000
        end_fmt = end_dt.replace(tzinfo=timezone.utc).timestamp() * 1000

        params = {
            "sensors": self.fields_to_scrape,
            "number": 4000,
            "startTs": start_fmt,
            "endTs": end_fmt,
        }

        url_to_call = (
            f"https://kunakcloud.com/openAPIv0/v1/rest/devices/{device_id}/reads/fromTo"
        )
        try:
            result = self.session.post(
                url_to_call, json=params, auth=(self.username, self.password)
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
        read it into Pandas as a long data frame and then pivot to wide, rather
        than do this manually in base Python.

        Args:
            - raw_data (dict): The data stored as a list of objects, with each object containing
            the keys ["ts", "sensor_tag", and "value"] giving the timestamp,
            measurand key, and measurement respectively.

        Returns:
            A 2D list representing the data in a tabular format, so that each
            row corresponds to a unique time-point and each column holds a
            measurand.
        """
        df = pd.DataFrame(raw_data, columns=["ts", "sensor_tag", "value"])
        df["value"] = df["value"].astype(
            float
        )  # For some reason pivot won't work on strings
        df["ts"] = pd.to_datetime(df["ts"], unit="ms")
        df["ts"] = df["ts"].dt.strftime("%Y-%m-%d %H:%M:%S")
        try:
            df_wide = df.pivot_table(
                index="ts", columns="sensor_tag", values="value", fill_value=""
            ).reset_index()
        except KeyError:
            raise DataParseError("Unable to pivot long to wide.")

        df_list = [df_wide.columns.tolist()] + df_wide.values.tolist()

        return df_list
