"""
    quantscraper.manufacturers.AQMesh.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Concrete implementation of Manufacturer, representing the AQMesh air
    quality instrumentation device manufacturer.
"""

from datetime import datetime, time
import json
import os
import requests as re
import pandas as pd
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

        # Authentication
        api_id = os.environ["AQMESH_API_ID"]
        licence = os.environ["AQMESH_API_TOKEN"]
        self.base_url = f"{cfg['base_url']}/{api_id}/{licence}"

        # Set general API settings
        self.data_url = "{base}/devicedata/{time}/AVG{avg}".format(
            base=self.base_url, time=cfg["time_convention"], avg=cfg["averaging_window"]
        )

        # Will cache all device operating conditions as when request them can
        # only obtain all devices at once, can't filter to a single device
        self.all_device_params = None

        super().__init__(cfg, fields)

    def connect(self):
        """
        Verifies the API token allows for authentication.

        The instance attribute 'session' stores a handle to the connection,
        holding any generated cookies and the history of requests.

        Args:
            - None.

        Returns:
            None, although a handle to the connection is stored in the instance
            attribute 'session'.
        """
        self.session = re.Session()
        url_to_call = "{base}/stations".format(base=self.base_url)

        try:
            result = self.session.get(url_to_call)
            result.raise_for_status()
        except re.exceptions.HTTPError as ex:
            raise LoginError(
                "HTTP error when verifying authentication.\n{}".format(str(ex))
            ) from None
        except re.exceptions.ConnectionError as ex:
            raise LoginError(
                "Connection error when verifying authentication.\n{}".format(str(ex))
            ) from None

        if result.text == "AUTHENTICATION FAILED":
            self.session.close()
            raise LoginError("Login failed, check credentials.")

    def log_device_status(self, device_id):
        """
        Scrapes information about a device's operating condition.

        This method does nothing for AQMesh, since the devices' calibration
        settings are already logged in the raw data.

        Args:
            - device_id (str): The ID used by the website to refer to the
                device.

        Returns:
            A dict of keyword-value parameters.
        """
        if self.all_device_params is None:
            url_to_call = f"{self.base_url}/devices"
            try:
                result = self.session.get(url_to_call)
                result.raise_for_status()
            except re.exceptions.HTTPError as ex:
                raise DataDownloadError(
                    "HTTP error when retrieving device status.\n{}".format(str(ex))
                ) from None
            except re.exceptions.ConnectionError as ex:
                raise DataDownloadError(
                    "Connection error when retrieving device status.\n{}".format(
                        str(ex)
                    )
                ) from None

            self.all_device_params = result.json()

        device_params = [
            x for x in self.all_device_params if str(x["UniqueId"]) == device_id
        ]
        if len(device_params) == 0:
            device_params = {}
        elif len(device_params) > 1:
            device_params = {}
        else:
            device_params = device_params[0]

        return device_params

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
            The data stored in a hierarchical format comprising dicts and lists.
            At the top level is a list of timepoints, represented as a dict
            containing measurements that are stored in a list of dicts in the
            'Channels' attribute.
        """
        # Convert start and end times into required format of
        # YYYY-mm-ddTHH:mm:ss
        # AQMesh API uses [closed, open] intervals, so set start time as midnight of
        # the start day, and end day as 23:59:59 of end day
        start_dt = datetime.combine(start, time.min)
        end_dt = datetime.combine(end, time.max)
        start_fmt = start_dt.strftime("%Y-%m-%dT%H:%M:%S")
        end_fmt = end_dt.strftime("%Y-%m-%dT%H:%M:%S")

        url_to_call = f"{self.data_url}/{start_fmt}/{end_fmt}/{device_id}"
        try:
            result = self.session.get(url_to_call)
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
            - raw_data (dict): The data stored in a hierarchical format comprising dicts and lists.
                At the top level is a list of timepoints, represented as a dict
                containing measurements that are stored in a list of dicts in the
                'Channels' attribute.

        Returns:
            A 2D list representing the data in a tabular format, so that each
            row corresponds to a unique time-point and each column holds a
            measurand.
        """
        clean_data = []
        for timepoint in raw_data.values():
            try:
                for channel in timepoint["Channels"]:
                    try:
                        clean_data.append(
                            {
                                "Timestamp": timepoint["Timestamp"]["Timestamp"],
                                "measurand": channel["SensorLabel"],
                                "value": channel["Scaled"]["Reading"],
                            }
                        )
                    except KeyError:
                        pass  # If don't have the Scaled or SensorLabel
                        # properties then skip to next measurement
            except KeyError:
                pass  # If don't have Channels object skip to next timepoint
        df = pd.DataFrame(clean_data)
        try:
            df_wide = df.pivot_table(
                index="Timestamp", columns="measurand", values="value", fill_value=""
            ).reset_index()
        except KeyError:
            raise DataParseError("Unable to pivot long to wide.")

        df_list = [df_wide.columns.tolist()] + df_wide.values.tolist()

        return df_list
