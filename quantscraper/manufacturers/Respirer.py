"""
    quantscraper.manufacturers.Respirer.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Concrete implementation of Manufacturer, representing the Respirer air
    quality instrumentation device manufacturer.
"""

from datetime import datetime, time, timedelta
import io
import os
import requests as re
import pandas as pd
from quantscraper.manufacturers.Manufacturer import Manufacturer
from quantscraper.utils import LoginError, DataDownloadError


class Respirer(Manufacturer):
    """
    Inherits attributes and methods from Manufacturer along with providing
    implementations of:
        - connect()
        - scrape_device()
        - parse_to_csv()
    """

    name = "RLS"

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
        self.avg_period = cfg["averaging_period"]
        self.avg_diff = cfg["averaging_diff"]
        self.time_zone = cfg["time_zone"]
        self.api_key = os.environ["RESPIRER_API_KEY"]

        super().__init__(cfg, fields)

    def connect(self):
        """
        Doesn't do anything as we have a permanent API token for the Respirer
        API.
        Just sets up a Session instance attribute to store a handle to the
        connection.

        Args:
            - None.

        Returns: 
            None, although a handle to the connection is stored in the instance
            attribute 'session'.
        """
        self.session = re.Session()

    def log_device_status(self, device_id):
        """
        This method does nothing for Respirer, since there isn't any means of
        obtaining device status from the API.

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
        Downloads the data for a given device from the API.

        Args:
            - device_id (str): The ID used by the website to refer to the
                device.
            - start (date): The start of the scraping window.
            - end (date): The end of the scraping window.

        Returns:
            The data is returned by the API in CSV format, i.e. as a string with
            '\n' separating new lines and commas delimiting fields.
        """
        # Respirer API uses [closed, open] intervals, so set start time as midnight of
        # the start day, and end day as midnight of following day
        start_dt = datetime.combine(start, time.min)
        end_dt = datetime.combine(end + timedelta(days=1), time.min)
        start_fmt = start_dt.strftime("%Y-%m-%dT%H:%M")
        end_fmt = end_dt.strftime("%Y-%m-%dT%H:%M")

        url_to_call = f"{self.base_url}/adp/v1/getDeviceDataLocal/imei/{device_id}/startdate/{start_fmt}/enddate/{end_fmt}/ts/{self.avg_period}/avg/{self.avg_diff}/api/{self.api_key}/time_zone/{self.time_zone}"
        header = {"Accept": "text/csv"}

        try:
            result = self.session.get(url_to_call, headers=header)
            result.raise_for_status()
        except re.exceptions.HTTPError as ex:
            raise DataDownloadError(
                "Cannot download data.\n{}".format(str(ex))
            ) from None
        except re.exceptions.ConnectionError as ex:
            raise DataDownloadError(
                "Connection error when downloading data.\n{}".format(str(ex))
            ) from None

        return result.text

    def parse_to_csv(self, raw_data):
        """
        Parses the raw data into a 2D list format.

        Pandas is used to parse the CSV formatted string.

        Args:
            - raw_data (dict): The data is returned by the API in CSV format,
               i.e. as a string with '\n' separating new lines and commas
               delimiting fields.

        Returns:
            A 2D list representing the data in a tabular format, so that each
            row corresponds to a unique time-point and each column holds a
            measurand.
        """
        df = pd.read_csv(io.StringIO(raw_data))
        df_list = [df.columns.values.tolist()] + df.values.tolist()
        return df_list
