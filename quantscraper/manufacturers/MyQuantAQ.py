import logging
import sys
from datetime import datetime, timedelta
from string import Template
from quantscraper.manufacturers.Manufacturer import Manufacturer
from quantscraper.utils import LoginError, DataDownloadError, DataParseError
import quantaq

# Need to avoid namespace issues with quantaq package
class MyQuantAQ(Manufacturer):
    name = "QuantAQ"

    def __init__(self, cfg):
        """
        Sets up object with parameters needed to scrape data.

        Args:
            - cfg: Instance of ConfigParser

        Returns:
            None
        """
        self.api_token = cfg.get(self.name, "api_token")
        self.device_ids = cfg.get(self.name, "devices").split(",")
        self.cols_to_validate = cfg.get(self.name, "columns_to_validate").split(",")
        self.timestamp_col = cfg.get(self.name, "timestamp_column")

        # Load start and end scraping datetimes
        start_datetime = cfg.get("Main", "start_time")
        end_datetime = cfg.get("Main", "end_time")
        start_date = datetime.fromisoformat(start_datetime).strftime("%Y-%m-%d")
        # Notice how we add on 1 day here.
        # The API only allows you to filter based on dates, not datetimes.
        # Secondly, although there is a "less than or equal to" filter,
        # if you use ">= start_date and <= end_date" where start_date=end_date,
        # i.e. the common scenario in our usage, then it raises an error.
        # The solution is to add a day onto the end_date,
        # and use < rather than <=
        end_date = datetime.fromisoformat(end_datetime)
        end_date = (end_date + timedelta(days=1)).strftime("%Y-%m-%d")

        # This would be more easily saved as a dict as that's how it gets used
        # later, but the quantaq package does some funny dict updating by
        # reference that modifies the dict from my environment
        raw = Template("timestamp,ge,${start};timestamp,lt,${end}")
        self.query_string = raw.substitute(start=start_date, end=end_date)

        super().__init__(cfg)

    def connect(self):
        """
        Overrides super method as not using requests.
        """
        self.api_obj = quantaq.QuantAQ(self.api_token)
        # Test connection by running basic query
        try:
            self.api_obj.get_account()
        except quantaq.baseapi.DataReadError as ex:
            raise LoginError(
                "Could not connect to quantaq API.\n{}".format(ex)
            ) from None

    def scrape_device(self, deviceID):
        """
        TODO
        """
        try:
            raw = self.api_obj.get_data(
                sn=deviceID, final_data=False, params=dict(filter=self.query_string),
            )
        except quantaq.baseapi.DataReadError as ex:
            raise DataDownloadError(
                "Cannot read data from QuantAQ's website:\n{}".format(ex)
            ) from None
        try:
            final = self.api_obj.get_data(
                sn=deviceID, final_data=True, params=dict(filter=self.query_string),
            )
        except quantaq.baseapi.DataReadError as ex:
            raise DataDownloadError(
                "Cannot read data from QuantAQ's website:\n{}".format(ex)
            ) from None

        data = {"raw": raw, "final": final}
        return data

    def parse_to_csv(self, raw_data):
        """
        TODO
        """
        # Raw data in format of list of dicts, each dict corresponds to a row
        # The main thing to look out for is that while the dictionary is
        # primarily in the format measurand: value, the 'geo' index holds a
        # secondary dict, which contains 'lat' and 'lon'.
        # There's also some metadata, such as 'url' and 'sn'.

        # I don't want to hardcode the columns to include, as there are some
        # columns here that are only present in the raw data and not the final
        # data (i.e. no2_ae and no2_we), and it would be better to have the same
        # code work for both raw and final data.
        raw_data = raw_data["final"]
        nrows = len(raw_data)
        if nrows < 1:
            raise DataParseError("No data found.")

        # Don't need url + sn and will handle geo separately
        measurands = list(raw_data[0].keys())
        if "geo" in measurands:
            measurands.remove("geo")
        if "url" in measurands:
            measurands.remove("url")
        if "sn" in measurands:
            measurands.remove("sn")

        # TODO Could automate the handling of lat/lon?
        # I.e. see if any dicts exist in data, and if so then expand them
        clean_data = []
        for i in range(nrows):
            row = []
            for measurand in measurands:
                try:
                    value = raw_data[i][measurand]
                except KeyError:
                    # TODO Currently use empty string to denote missingness,
                    # should we use a custom error code to help later debugging?
                    value = ""
                row.append(value)
            row.append(raw_data[i]["geo"]["lat"])
            row.append(raw_data[i]["geo"]["lon"])
            clean_data.append(row)

        # Add headers
        clean_data.insert(0, measurands + ["lat", "lon"])

        return clean_data
