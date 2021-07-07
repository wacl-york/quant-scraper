"""
    quantscraper.manufacturers.Clarity.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Concrete implementation of Manufacturer, representing the Clarity air
    quality instrumentation device manufacturer.
"""

from datetime import datetime, time
import json
import os
import requests as re
import pandas as pd
from quantscraper.manufacturers.Manufacturer import Manufacturer
from quantscraper.utils import LoginError, DataDownloadError, DataParseError


class Clarity(Manufacturer):
    """
    Inherits attributes and methods from Manufacturer along with providing
    implementations of:
        - connect()
        - scrape_device()
        - parse_to_csv()
    """

    name = "Clarity"

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
        self.base_url = cfg["base_url"]
        self.limit = cfg["limit"]
        self.skip = cfg["skip"]
        self.auth_header = {
            "x-api-key": os.environ["CLARITY_API_KEY"],
            "Accept-Encoding": "gzip",
        }

        super().__init__(cfg, fields)

    def connect(self):
        """
        Connects to the API.

        Unused for Clarity since no explicit connection step is required,
        instead the pre-generated API key is passed in with every request.
        Simply creates a `session`.

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

        You can't request a specific device's status with the Clarity API, so
        this method instead requests all device statuses and filters to the
        specific one afterwards.

        Args:
            - device_id (str): The ID used by the website to refer to the
                device.

        Returns:
            A dict of keyword-value parameters.
        """
        url_to_call = f"{self.base_url}/devices"
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

        params = [x for x in result.json() if x["code"] == device_id][0]
        return params

    def scrape_device(self, device_id, start, end):
        """
        Downloads the data for a given device from the website.

        This just requires a single API GET request with the appropriate params,
        returning a JSON object containing the data.

        Args:
            - device_id (str): The ID used by the website to refer to the
                device.
            - start (date): The start of the scraping window.
            - end (date): The end of the scraping window.

        Returns:
            The raw data stored in JSON format.
            See the documentation at
            https://clarity-public.s3-us-west-2.amazonaws.com/documents/Clarity+Air+Monitoring+Network+REST+API+Documentation.html
            for specifis
        """
        # Convert start and end times into required format of
        # YYYY-mm-ddTHH:mm:ss
        # Clarity API uses [closed, open] intervals, so set start time as midnight of
        # the start day, and end day as 23:59:59 of end day
        start_dt = datetime.combine(start, time.min)
        end_dt = datetime.combine(end, time.max)
        start_fmt = start_dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_fmt = end_dt.strftime("%Y-%m-%dT%H:%M:%SZ")

        params = {
            "code": device_id,
            "startTime": start_fmt,
            "endTime": end_fmt,
            "skip": self.skip,
            "limit": self.limit,  # Request as much data as possible
        }

        url_to_call = f"{self.base_url}/measurements"
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

        return data

    def parse_to_csv(self, raw_data):
        """
        Parses the raw data into a 2D list format.

        Since the raw data is in a JSON format, it is easier to
        read it into Pandas as a DataFrame and then convert to a 2D list.

        Args:
            - raw_data (dict): The raw data as returned by the API. See the
            documentation for the specific structure.
        https://clarity-public.s3-us-west-2.amazonaws.com/documents/Clarity+Air+Monitoring+Network+REST+API+Documentation.html

        Returns:
            A 2D list representing the data in a tabular format, so that each
            row corresponds to a unique time-point and each column holds a
            measurand.
        """
        clean_data = []
        for item in raw_data:
            try:
                record = {"timestamp": item["time"]}
                for characteristic in item["characteristics"]:
                    record[characteristic] = item["characteristics"][characteristic][
                        "value"
                    ]
                clean_data.append(record)
            except KeyError:
                # Skip to next record if any errors with this one
                pass
        df = pd.DataFrame(clean_data)
        df_list = [df.columns.tolist()] + df.values.tolist()

        return df_list
