import sys
import logging
from datetime import datetime
from string import Template
from bs4 import BeautifulSoup
import requests as re
from quantscraper.manufacturers.Manufacturer import Manufacturer
from quantscraper.utils import LoginError, DataDownloadError, DataParseError


class Zephyr(Manufacturer):
    name = "Zephyr"

    def __init__(self, cfg):
        """
        Sets up object with parameters needed to scrape data.

        Args:
            - cfg: Instance of ConfigParser

        Returns:
            None
        """
        self.auth_url = cfg.get(self.name, "auth_url")
        self.device_ids = cfg.get(self.name, "devices").split(",")
        self.averaging_window = cfg.get(self.name, "averaging_window")
        self.slot = cfg.get(self.name, "slot")
        self.cols_to_validate = cfg.get(self.name, "columns_to_validate").split(",")
        self.timestamp_col = cfg.get(self.name, "timestamp_column")
        self.timestamp_format = cfg.get(self.name, "timestamp_format")

        # Authentication
        self.auth_params = {
            "username": cfg.get(self.name, "username"),
            "password": cfg.get(self.name, "password"),
            "grant_type": "password",
        }
        self.auth_headers = {"referer": cfg.get(self.name, "auth_referer")}

        # Download data
        self.data_headers = {"content-type": "application/json; charset=UTF-8"}

        # Load start and end scraping datetimes
        start_datetime = cfg.get("Main", "start_time")
        end_datetime = cfg.get("Main", "end_time")
        start_date = datetime.fromisoformat(start_datetime).strftime("%Y%m%d%H%M%S")
        end_date = datetime.fromisoformat(end_datetime).strftime("%Y%m%d%H%M%S")

        self.start_date = start_date
        self.end_date = end_date

        raw_data_url = cfg.get(self.name, "data_url")
        self.data_url = Template(
            raw_data_url + "/${token}/${device}/${start}/${end}/AB/newDef/6/JSON/api"
        )

        # This field gets set in self.connect()
        self.api_token = None

        super().__init__(cfg)

    def connect(self):
        """
        Overrides super method as needs to obtain API token
        """
        self.session = re.Session()

        try:
            result = self.session.post(
                self.auth_url, data=self.auth_params, headers=self.auth_headers
            )
            result.raise_for_status()
        except re.exceptions.HTTPError as ex:
            raise LoginError("HTTP error when logging in.\n{}".format(ex)) from None

        # Set api_token if above didn't raise HTTPError at any non-200 status
        self.api_token = result.json()["access_token"]
        # Would typically like to confirm authentication here, but this post
        # request returns an access token for _any_ username/password
        # combination. Only find out later when try to pull data if credentials
        # are incorrect.

    def scrape_device(self, deviceID):
        """
        TODO
        """
        this_url = self.data_url.substitute(
            device=deviceID,
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

        data = result.json()
        return data

    def parse_to_csv(self, raw_data):
        """
        TODO
        """
        # TODO Is it appropriate to log from this method?
        # Input raw data has 4 fields:
        #   - errorDesc: Potentially useful for error handling, will keep a note
        #   of it. So far has just had None
        #   - data: Payload of interest
        #   - queryInfo: query params, not useful except potentially debugging
        #   - info: Looks like info for webpage, as has HMTL markup

        # data has 5 fields for different averaging strategies:
        #   - unaveraged (what I assume we want)
        #   - 15 mins on quarter hours
        #   - daily average at midnight
        #   - hourly average on the hour
        #   - 8 hour average at midnight and 8am and 4pm
        raw_data = raw_data["data"]
        raw_data = raw_data[self.averaging_window]

        # This data has 2 fields:
        #   slotA and slotB.
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
                else:
                    logging.info("{} has data so will pull it.".format(remaining_slot))
                    parsed_data = raw_data[remaining_slot]

        # Parsed data is now a dictionary:
        # parsed_data= {measurand: {
        #                           header: [],
        #                           data: [],
        #                           data_hash: str
        #                          }
        # The 'header' entries contain metadata, such as label, units, order in
        # output csv
        # 'data' is the list of values, and 'data_hash' is just a hash

        # Obtain fields in CSV order
        measurands = list(parsed_data.keys())
        measurands.sort(key=lambda x: parsed_data[x]["header"]["CSVOrder"])

        # Check have same number of rows for each field
        nrows = [len(parsed_data[measurand]["data"]) for measurand in measurands]
        if not len(set(nrows)) == 1:
            raise DataParseError(
                "Fields have differing number of observations: {}".format(nrows)
            )

        # Form into CSV. Not most effecient solution but will do for now
        # Could make into 2D list comp, not very readable but quicker
        # Or there's probably an internal Python function from itertools or
        # something that is more efficient
        clean_data = []
        for i in range(nrows[0]):
            row = [parsed_data[col]["data"][i] for col in measurands]
            clean_data.append(row)

        # Add header row
        clean_data.insert(0, measurands)

        return clean_data
