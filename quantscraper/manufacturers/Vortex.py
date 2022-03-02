"""
    quantscraper.manufacturers.Vortex.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Concrete implementation of Manufacturer, representing the Vortex air
    quality instrumentation device manufacturer.
"""

from datetime import datetime, time
import json
import logging
import os
import requests as re
import pandas as pd
from quantscraper.manufacturers.Manufacturer import Manufacturer
from quantscraper.utils import LoginError, DataDownloadError


class Vortex(Manufacturer):
    """
    Inherits attributes and methods from Manufacturer along with providing
    implementations of:
        - connect()
        - scrape_device()
        - parse_to_csv()
    """

    name = "Vortex"

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
        self.raw_data_cache = {}

        self.base_url = cfg["base_url"]
        self.api_url = cfg["api_url"]
        self.auth_params = {
            "email": os.environ["VORTEX_USER"],
            "password": os.environ["VORTEX_PW"],
        }
        self.deployment_id = cfg["deployment_id"]

        super().__init__(cfg, fields)

    def connect(self):
        """
        Connects to the API and obtains an authorization token for data
        requests.

        The instance attribute 'session' stores a handle to the connection.

        Args:
            - None.

        Returns:
            None, although a handle to the connection is stored in the instance
            attribute 'session'.
        """
        self.session = re.Session()

        # Obtain API token
        url_to_call = f"{self.base_url}/authenticate"
        try:
            result = self.session.post(
                url_to_call,
                json=self.auth_params,
                headers={
                    "Accept": "application/json",
                    "Content-Type": "application/json",
                },
            )
            result.raise_for_status()
        except re.exceptions.HTTPError as ex:
            raise LoginError("Cannot authenticate.\n{}".format(str(ex))) from None
        except re.exceptions.ConnectionError as ex:
            raise LoginError(
                "Connection error when authenticating.\n{}".format(str(ex))
            ) from None

        payload = result.json()
        self.access_token = payload["accessToken"]

        # Validate the token
        url_to_call = f"{self.api_url}/validate"
        try:
            result = self.session.get(
                url_to_call, headers={"Authorization": self.access_token}
            )
            result.raise_for_status()
        except re.exceptions.HTTPError as ex:
            raise LoginError("Cannot validate API token.\n{}".format(str(ex))) from None
        except re.exceptions.ConnectionError as ex:
            raise LoginError(
                "Connection error when validating API token.\n{}".format(str(ex))
            ) from None

        if result.text != "Successfully validated token":
            raise LoginError("Unable to validate API token.") from None

    def log_device_status(self, device_id):
        """
        Scrapes information about a device's operating condition.

        This method does nothing for Vortex as there isn't an API endpoint for
        device metadata.

        Args:
            - device_id (str): The ID used by the website to refer to the
                device.

        Returns:
            A dict of keyword-value parameters.
        """
        params = {}
        return params

    def scrape_device(self, device_id, start, end):
        """
        Downloads the data for a given device from the website.

        The Vortex API only provides data for all devices at the same time, so
        the first time a device is scraped in a session a local cache is made of
        data from all devices which is later accessed when subsequent devices
        are requested to be scraped.

        An additional complication is that the gas and PM channels need to be
        requested separately.

        Args:
            - device_id (str): The ID used by the website to refer to the
                device.
            - start (date): The start of the scraping window.
            - end (date): The end of the scraping window.

        Returns:
            A dictionary with "GAS" and "PM" objects, each of which comprises of
            a list of dicts, where each dict corresponds to a timepoint and
            holds several measurements.
        """
        # Convert start and end times into required format of
        # YYYY-mm-dd HH:MM
        # Vortex API uses [closed, open] intervals
        start_dt = datetime.combine(start, time.min)
        end_dt = datetime.combine(end, time.max)
        start_fmt = start_dt.strftime("%Y-%m-%d %H:%M")
        end_fmt = end_dt.strftime("%Y-%m-%d %H:%M")

        date_key = "_".join((start_fmt, end_fmt))
        try:
            raw_data = self.raw_data_cache[date_key][device_id]
        except KeyError:
            # Data isn't available in the cache for this device
            self.download_data_to_cache(start_fmt, end_fmt, date_key)
            try:
                raw_data = self.raw_data_cache[date_key][device_id]
            except KeyError:
                raise DataDownloadError("Cannot retrieve data from cache")

        return raw_data

    def download_data_to_cache(self, start, end, date_key):
        """
        Downloads data for a given time period and saves it in a local cache.

        The local cache is an instance variable self.raw_data_cache, indexed by
        a scraping period.

        Args:
            - start (str): The start of the scraping window in YYYY-mm-dd
                HH:MM format.
            - end (str): The end of the scraping window in YYYY-mm-dd HH:MM
                format.
            - date_key (str): The key to use for the cache.

        Returns:
            None, stores data in the self.raw_data_cache[date_key] object
            as a side-effect.
        """
        # Set raw data cache for every sensor and gas/pm channels
        if date_key not in self.raw_data_cache:
            self.raw_data_cache[date_key] = {}

        for channel in ["GAS", "PM"]:
            raw_data = self.download_channel(channel, start, end)

            # The raw data comes as a list of objects for each sensor
            for device_obj in raw_data:
                device_id = device_obj["sensorId"]
                if device_id not in self.raw_data_cache[date_key]:
                    self.raw_data_cache[date_key][device_id] = {}
                self.raw_data_cache[date_key][device_id][channel] = device_obj[
                    "readings"
                ]

    def download_channel(self, reading_type, start, end):
        """
        Downloads a specific channel of data for all devices from the Vortex
        API.

        Args:
            - reading_type (str): The channel type to request data for, either
                'GAS', or 'PM'.
            - start (str): The start of the scraping window in YYYY-mm-dd
                HH:MM format.
            - end (str): The end of the scraping window in YYYY-mm-dd HH:MM
                format.

        Returns:
            A list of dicts where each dict corresponds to a different device.
            The dicts have 2 keys: 'sensorId' and 'readings'. 'sensorId' is a
            string giving the device id and 'readings' is a list of dicts
            containing the measurements at each timepoint.
        """
        url_to_call = f"{self.api_url}/v2/readings"
        params = {
            "deploymentId": self.deployment_id,
            "readingType": reading_type,
            "output": "json",
            "start": start,
            "end": end,
        }

        try:
            result = self.session.get(
                url_to_call, params=params, headers={"Authorization": self.access_token}
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
        data = json.loads(result.text)
        return data

    def parse_to_csv(self, raw_data):
        """
        Parses the raw data into a 2D list format.

        The raw JSON data is loaded into a Pandas DataFrame and then converted
        into a 2D list from there.

        Args:
            - raw_data (dict): A dictionary with "GAS" and "PM" objects, each of which comprises of a list of dicts, where each dict corresponds to a timepoint and holds several measurements.

        Returns:
            A 2D list representing the data in a tabular format, so that each
            row corresponds to a unique time-point and each column holds a
            measurand.
        """
        key_cols = ["timestamp", "sensorEuid", "sensorId", "coords"]
        try:
            df_gas = pd.DataFrame(raw_data["GAS"])
        except KeyError:
            logging.warning("Missing gas data")
            df_gas = pd.DataFrame(columns=key_cols)
        try:
            df_pm = pd.DataFrame(raw_data["PM"])
        except KeyError:
            logging.warning("Missing PM data")
            df_pm = pd.DataFrame(columns=key_cols)

        df_comb = df_gas.merge(df_pm, how="outer", on=key_cols)
        df_comb["timestamp"] = pd.to_datetime(df_comb["timestamp"], unit="ms")
        df_comb["timestamp"] = df_comb["timestamp"].dt.strftime("%Y-%m-%d %H:%M:%S")

        df_list = [df_comb.columns.tolist()] + df_comb.values.tolist()
        return df_list
