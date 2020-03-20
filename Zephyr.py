from datetime import datetime
from string import Template
import requests as re
from Manufacturer import Manufacturer


class Zephyr(Manufacturer):
    @property
    def name(self):
        """
        Manufacturer name, as used as a section in the config file.
        """
        return "Zephyr"

    def __init__(self, cfg):
        """
        Sets up object with parameters needed to scrape data.

        Args:
            - cfg: Instance of ConfigParser

        Returns:
            None
        """
        self.username = cfg.get(self.name, "username")
        self.password = cfg.get(self.name, "password")
        self.auth_url = cfg.get(self.name, "auth_url")
        self.auth_referer = cfg.get(self.name, "auth_referer")
        self.device_ids = cfg.get(self.name, "devices").split(",")

        # Authentication
        self.auth_params = {
            "username": self.username,
            "password": self.password,
            "grant_type": "password",
        }
        self.auth_headers = {"referer": self.auth_referer}

        # Download data
        self.data_headers = {"content-type": "application/json; charset=UTF-8"}

        # Load start and end scraping datetimes
        start_datetime = cfg.get("Main", "start_time")
        end_datetime = cfg.get("Main", "end_time")
        start_date = datetime.fromisoformat(start_datetime).strftime("%Y%m%d%H%M%S")
        end_date = datetime.fromisoformat(end_datetime).strftime("%Y%m%d%H%M%S")

        self.start_date = start_date
        self.end_date = end_date

        # TODO Debug and see if these parameters (AB/newDef/6) are hardcoded
        raw_data_url = cfg.get(self.name, "data_url")
        self.data_url = Template(
            raw_data_url + "/${token}/${device}/${start}/${end}/AB/newDef/6/JSON/api"
        )

        super().__init__(cfg)

    def connect(self):
        """
        Overrides super method as needs to obtain API token
        """
        self.session = re.Session()
        result = self.session.post(
            self.auth_url, data=self.auth_params, headers=self.auth_headers
        )

        if result.status_code != re.codes["ok"]:
            # TODO convert to log
            print("Error: cannot connect")
            return False
        else:
            self.api_token = result.json()["access_token"]
            return True

    def scrape_device(self, deviceID):
        """
        TODO
        """
        # TODO Replace ALL format calls with substitute where allowing user
        # input
        this_url = self.data_url.substitute(
            device=deviceID,
            token=self.api_token,
            start=self.start_date,
            end=self.end_date,
        )
        # TODO Multiple returns, not ideal
        result = self.session.get(this_url, headers=self.data_headers,)
        if result.status_code != re.codes["ok"]:
            print("Error: cannot download data")
            return None
        data = result.json()

        return data

    def process_device(self, deviceID):
        """
        TODO
        """
        # TODO Can change this to use property getter?
        # Has 4 fields:
        #   - errorDesc: Potentially useful for error handling, will keep a note
        #   of it. So far has just had None
        #   - data: Payload of interest
        #   - queryInfo: query params, not useful except potentially debugging
        #   - info: Looks like info for webpage, as has HMTL markup
        raw = self._raw_data[deviceID]

        # data has 5 fields for different averaging strategies:
        #   - unaveraged (what I assume we want)
        #   - 15 mins on quarter hours
        #   - daily average at midnight
        #   - hourly average on the hour
        #   - 8 hour average at midnight and 8am and 4pm
        raw_data = raw["data"]
        raw_data = raw_data["Unaveraged"]

        # This data has 2 fields:
        #   slotA and slotB.
        # So far I've never seen slotA populated, but best to check
        if raw_data["slotB"] is None:
            print("slotB is empty")

            if raw_data["slotA"] is None:
                print("slotA is also empty")
            else:
                print("slotA has data so will pull it")
                parsed_data = raw_data["slotA"]
        else:
            parsed_data = raw_data["slotB"]

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
        same_length = len(set(nrows)) == 1
        if not same_length:
            print("Fields have differing number of observations: {}".format(nrows))

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
