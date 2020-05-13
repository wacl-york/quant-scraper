"""
    quantscraper.manufacturers.Zephyr.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Concrete implementation of Manufacturer, representing the Zephyr air
    quality instrumentation device manufacturer.
"""

import logging
from datetime import datetime, timedelta, time
import os
from string import Template
import requests as re
from quantscraper.manufacturers.Manufacturer import Manufacturer
from quantscraper.utils import LoginError, DataDownloadError, DataParseError


class Zephyr(Manufacturer):
    """
    Inherits attributes and methods from Manufacturer along with providing
    implementations of:
        - connect()
        - scrape_device()
        - parse_to_csv()
    """

    name = "Zephyr"

    def __init__(self, start_datetime, end_datetime, cfg, fields):
        """
        Sets up object with parameters needed to scrape data.

        Args:
            - start_datetime (datetime): The start of the scraping window.
            - end_datetime (datetime): The end of the scraping window.
            - cfg (dict): Keyword-argument properties set in the Manufacturer's
                'properties' attribute.
            - fields (list): List of dicts detailing the measurands available
                for this manufacturer and their properties.

        Returns:
            None
        """
        self.session = None
        self.auth_url = cfg["auth_url"]
        self.averaging_window = cfg["averaging_window"]
        self.slot = cfg["slot"]

        # Authentication
        self.auth_params = {
            "username": os.environ["ZEPHYR_USER"],
            "password": os.environ["ZEPHYR_PW"],
            "grant_type": "password",
        }
        self.auth_headers = {"referer": cfg["auth_referer"]}

        # Download data
        self.data_headers = {"content-type": "application/json; charset=UTF-8"}

        # Load start and end scraping datetimes
        # Zephyr uses [closed, open) intervals, so set start time as midnight of
        # the start day, and end day as midnight of day AFTER required end day.
        # Otherwise, if set end datetime to 23:59:59 of end day, then lose the
        # 59th minute worth of data
        start_dt = datetime.combine(start_datetime, time.min)
        end_dt = datetime.combine((end_datetime + timedelta(days=1)), time.min)
        start_fmt = start_dt.strftime("%Y%m%d%H%M%S")
        end_fmt = end_dt.strftime("%Y%m%d%H%M%S")
        self.start_date = start_fmt
        self.end_date = end_fmt

        raw_data_url = cfg["data_url"]
        self.data_url = Template(
            raw_data_url + "/${token}/${device}/${start}/${end}/AB/newDef/6/JSON/api"
        )

        # This field gets set in self.connect()
        self.api_token = None

        super().__init__(cfg, fields)

    def connect(self):
        """
        Establishes an HTTP connection to the AQMesh website.

        Logs in with username and password and obtains an API token.

        Would typically like to confirm authentication in this method,
        but the POST request returns an access token for *any* username/password
        regardless of whether the credentials are correct.

        An unsuccesful login attempt is only identified later when attempting
        to use the (invalid) API token.

        The instance attribute 'session' stores a handle to the connection,
        holding any generated cookies and the history of requests.

        Args:
            - None.

        Returns:
            None, although a handle to the connection is stored in the instance
            attribute 'session' and the API token is also saved as an instance
            attribute.
        """
        self.session = re.Session()

        try:
            result = self.session.post(
                self.auth_url, data=self.auth_params, headers=self.auth_headers
            )
            result.raise_for_status()
        except re.exceptions.HTTPError as ex:
            raise LoginError("HTTP error when logging in.\n{}".format(ex)) from None
        except re.exceptions.ConnectionError as ex:
            raise LoginError(
                "Connection error when logging in.\n{}".format(ex)
            ) from None

        self.api_token = result.json()["access_token"]

    def scrape_device(self, device_id):
        """
        Downloads the data for a given device from the website.

        This just requires a single GET request with the query parameters are
        hardcoded into the URL itself.

        I.e. the URL to download data is in the form:
        <main domain>/<api token>/<device id>/<start date>/<end date>/AB/newDef/6/JSON/api

        Instead of passing in keyword-value arguments in the usual form of:
        <main domain>?device=foo&start_date=bar...

        Args:
            device_id (str): The website device_id to scrape for.

        Returns:
            The raw data is returned in the response's JSON and organised in a
            hierarchical format of dicts and lists.
        """
        this_url = self.data_url.substitute(
            device=device_id,
            token=self.api_token,
            start=self.start_date,
            end=self.end_date,
        )
        try:
            result = self.session.get(this_url, headers=self.data_headers,)
            result.raise_for_status()
        except re.exceptions.HTTPError as ex:
            raise DataDownloadError(
                "Cannot download data.\n{}".format(str(ex))
            ) from None
        except re.exceptions.ConnectionError as ex:
            raise DataDownloadError(
                "Connection error when downloading data.\n{}".format(str(ex))
            ) from None

        data = result.json()
        return data

    def parse_to_csv(self, raw_data):
        """
        Parses the raw data into a 2D list format.

        I'll document the data format here as there are several levels to it.

        The raw data has 4 fields:
          - errorDesc: Potentially useful for error handling, will keep a note
          of it. So far has just had None
          - data: Payload of interest
          - queryInfo: query params, not useful except potentially debugging
          - info: Looks like info for webpage, as has HMTL markup

        The 'data' attribute has 5 fields for different averaging strategies:
          - unaveraged
          - 15 mins on quarter hours
          - daily average at midnight
          - hourly average on the hour
          - 8 hour average at midnight and 8am and 4pm

        Once the averaging attribute has been selected, a new dict is
        encountered with 2 fields:
          'slotA' and 'slotB'.
        So far I've never seen slotA populated, but the code checks for data
        existing in both, as it is not documented what the slots represent,
        and we cannot assume that data will always be in slotB.

        The non-empty slot holds another dictionary, mapping each measurand to
        its recorded values and associated meta-data:
        {
            measurand: {
                        header: [],
                        data: [],
                        data_hash: str
                       },
            measurand2: ...
        }
        'data' is the recorded values themselves.
        The 'header' entries contain metadata, such as label, units, and order
        in the output csv that can be downloaded from the website.

        Args:
            - raw_data (dict): The raw data is organised in a
                hierarchical format of dicts and lists, containing a large
                amount of metadata. See above for full documentation.

        Returns:
            A 2D list representing the data in a tabular format, so that each
            row corresponds to a unique time-point and each column holds a
            measurand.
        """
        # TODO is it fair to log from this method? Have removed it from all
        # other Manufacturer methods, but useful here to log any irregularities
        # with the data, since we don't understand exactly what the difference
        # between 'slotA' and 'slotB' is.

        raw_data = raw_data["data"]
        raw_data = raw_data[self.averaging_window]

        # So far I've never seen slotA populated, but best to check
        try:
            parsed_data = raw_data[self.slot]
            if parsed_data is None:
                raise KeyError
        except KeyError:
            logging.warning("Chosen slot '{}' is empty".format(self.slot))
            # See if have data in another slot
            slot_keys = list(raw_data.keys())
            if self.slot in slot_keys:
                slot_keys.remove(self.slot)

            if len(slot_keys) == 1:
                logging.info(
                    "There is one other slot, can see if it has data: {}".format(
                        slot_keys
                    )
                )

                remaining_slot = slot_keys[0]

                if raw_data[remaining_slot] is None:
                    logging.warning("{} is also empty.".format(remaining_slot))
                    raise DataParseError("No data available in any slots.")

                logging.info("{} has data so will pull it.".format(remaining_slot))
                parsed_data = raw_data[remaining_slot]

        # Obtain fields in CSV order
        measurands = list(parsed_data.keys())
        measurands.sort(key=lambda x: parsed_data[x]["header"]["CSVOrder"])

        # Check have same number of rows for each field
        nrows = [len(parsed_data[measurand]["data"]) for measurand in measurands]
        if not len(set(nrows)) == 1:
            raise DataParseError(
                "Fields have differing number of observations: {}".format(nrows)
            )

        # Form into CSV. Not most efficient solution but will do for now
        # There's probably a function from itertools that is more efficient
        clean_data = []
        for i in range(nrows[0]):
            row = [parsed_data[col]["data"][i] for col in measurands]
            clean_data.append(row)

        # Add header row
        clean_data.insert(0, measurands)

        return clean_data
