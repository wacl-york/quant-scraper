"""
    quantscraper.manufacturers.SouthCoastScience.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Concrete implementation of Manufacturer, representing the SouthCoastScience air
    quality instrumentation device manufacturer.
"""

from datetime import datetime, time, timedelta
import urllib.parse
import json
import os
import requests as re
import pandas as pd
from quantscraper.manufacturers.Manufacturer import Manufacturer
from quantscraper.utils import LoginError, DataDownloadError, DataParseError


class SouthCoastScience(Manufacturer):
    """
    Inherits attributes and methods from Manufacturer along with providing
    implementations of:
        - connect()
        - scrape_device()
        - parse_to_csv()
    """

    name = "SCS"

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
        self.topic_prefix = cfg["topic_prefix"]
        self.checkpoint = cfg["averaging_checkpoint"]
        self.headers = {
            "Accept": "application/json",
            "Authorization": os.environ["SCS_API_KEY"],
        }

        super().__init__(cfg, fields)

    def connect(self):
        """
        Connects to the API.

        For South Coast Science no authorization step is required - a
        predetermined API key is attached to every request - so this method
        simply sets up a `session` instance attribute.

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

        This method is not implemented for South Coast Science.

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

        Data is accessed through 3 "topics", each requiring a separate GET
        request:
            - gases
            - particulate matter
            - meteorological

        Args:
            - device_id (str): The ID used by the website to refer to the
                device.
            - start (date): The start of the scraping window.
            - end (date): The end of the scraping window.

        Returns:
            This function returns a dict with 3 objects for each of the channels
            with keys 'gas', 'pm', and 'met'. Each object is the data from that
            topic as returned by the API.
        """
        # SCS API uses slightly confusing non-strict ]open, closed] intervals
        # To get recordings starting from - and including - midnight we provide
        # a start time of 23:58:59 from the previous day.
        # To get data up to and including 23:59 from a day, we provide an end
        # time of 23:58:59.
        # For some undocumented reason, requesting a start time of 23:59:59 (day
        # before) or 00:00:00 both return data starting at 00:01:00, and
        # requesing an end time of 23:59:59 has a last timepoint at 00:00:00
        start_dt = datetime.combine(start - timedelta(days=1), time.max) - timedelta(
            minutes=1
        )
        end_dt = datetime.combine(end, time.max) - timedelta(minutes=1)
        start_fmt = start_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        end_fmt = end_dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")
        params = {
            "startTime": start_fmt,
            "endTime": end_fmt,
            "checkpoint": self.checkpoint,
        }

        # Need to request gas/pm/met separately
        raw_data = {}
        topic_ids = {"gas": "gases", "pm": "particulates", "met": "climate"}
        for type, topic_id in topic_ids.items():
            params["topic"] = f"{self.topic_prefix}/{device_id}/{topic_id}"
            url = f"{self.base_url}?{urllib.parse.urlencode(params)}"
            raw_data[type] = self.retrieve_topic(url, self.headers)

        return raw_data

    def parse_to_csv(self, raw_data):
        """
        Parses the raw data into a 2D list format.

        Since the raw data is already in a hierarchical format, it is easier to
        read it into Pandas rather than try to parse it ourselves.
        The only challenge here is that the format differs slightly between the
        3 topics (gases, pm, met), as there are differing number of levels in
        the hierarchy. Hence 3 different parsers are required.

        The resultant 3 DataFrames are then merged into a single one that is
        converted back into standard Python data structures.

        Args:
            - raw_data (dict): The data stored in a hierarchical format, with
            the top level dictionary indexed by topic ('gas', 'pm', or 'met').

        Returns:
            A 2D list representing the data in a tabular format, so that each
            row corresponds to a unique time-point and each column holds a
            measurand.
        """
        df_gas = self.gas_json_to_dataframe(raw_data["gas"])
        df_pm = self.pm_json_to_dataframe(raw_data["pm"])
        df_met = self.met_json_to_dataframe(raw_data["met"])
        try:
            df_comb = pd.merge(df_gas, df_pm, on="timestamp", how="outer")
            df_comb = pd.merge(df_comb, df_met, on="timestamp", how="outer")
        except KeyError:
            raise DataParseError("No 'timestamp' field in data to join on.")

        df_list = [df_comb.columns.tolist()] + df_comb.values.tolist()
        return df_list

    def retrieve_topic(self, url, headers):
        """
        Scrapes all available data from a specific topic.

        The API paginates its responses into 1000 items at a time.
        This function simply iteratively calls the API until all records have
        been pulled.

        Args:
            - url (string): The topic URL to GET.
            - headers (dict): HTTP headers to send with the request.

        Returns:
            A 2D list representing the data in a tabular format, so that each
            row corresponds to a unique time-point and each column holds a
            measurand.
        """
        raw_data = []

        while True:
            try:
                result = self.session.get(url, headers=headers)
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
                raise DataDownloadError(
                    "No 'Data' attribute in downloaded json."
                ) from None

            raw_data.extend(data["Items"])

            try:
                url = data["next"]
            except KeyError:
                break

        return raw_data

    def gas_json_to_dataframe(self, input):
        """
        Converts gas data stored as JSON objects into a Pandas DataFrame.

        Args:
            - input (list): A list of gas records stored as JSON objects.

        Returns:
            A Pandas.DataFrame containing the data. Will have a 'timestamp'
            column with multiple measurement columns.
        """
        data = []
        for item in input:
            # Expand all raw measurements per gas except T/RH
            raw_dict = {
                f"{key}_{innerkey}": item["val"][key][innerkey]
                for key in item["val"]
                for innerkey in item["val"][key]
                if key != "sht"
            }

            # Add exogeneses (aka calibrated) fields
            # NB: these are nested 3 objects deep, whereas PM are 2 deep
            exg_dict = {
                f"exg_{key1}_{key2}_{key3}": item["exg"][key1][key2][key3]
                for key1 in item["exg"].keys()
                for key2 in item["exg"][key1].keys()
                for key3 in item["exg"][key1][key2].keys()
            }
            raw_dict.update(exg_dict)

            # Add timestamp
            raw_dict["timestamp"] = item["rec"]
            data.append(raw_dict)
        return pd.DataFrame(data)

    def pm_json_to_dataframe(self, input):
        """
        Converts pm data stored as JSON objects into a Pandas DataFrame.

        Args:
            - input (list): A list of pm records stored as JSON objects.

        Returns:
            A Pandas.DataFrame containing the data. Will have a 'timestamp'
            column with multiple measurement columns.
        """
        data = []
        for item in input:
            # Grab all raw measurements except T/RH
            raw_dict = {
                key: item["val"][key]
                for key in item["val"]
                if key not in ("bin", "sht")
            }
            # Add bin
            for idx, measurement in enumerate(item["val"]["bin"]):
                raw_dict[f"bin_{idx+1}"] = measurement

            # Add exogeneses (aka calibrated) fields
            exg_dict = {
                f"exg_{key1}_{key2}": item["exg"][key1][key2]
                for key1 in item["exg"].keys()
                for key2 in item["exg"][key1].keys()
            }
            raw_dict.update(exg_dict)

            # Add timestamp
            raw_dict["timestamp"] = item["rec"]
            data.append(raw_dict)
        return pd.DataFrame(data)

    def met_json_to_dataframe(self, input):
        """
        Converts met data stored as JSON objects into a Pandas DataFrame.

        Args:
            - input (list): A list of met records stored as JSON objects.

        Returns:
            A Pandas.DataFrame containing the data. Will have a 'timestamp'
            column with multiple measurement columns.
        """
        data = []
        for item in input:
            # Grab all raw measurements except pressure, which is nested for
            # some reason
            raw_dict = {
                key: item["val"][key] for key in item["val"] if key not in ("bar")
            }
            # Add pressure
            raw_dict["bar_pA"] = item["val"]["bar"]["pA"]

            # Add timestamp
            raw_dict["timestamp"] = item["rec"]
            data.append(raw_dict)
        return pd.DataFrame(data)
