import sys
from datetime import datetime, timedelta
from string import Template
from Manufacturer import Manufacturer
import quantaq

# Need to avoid namespace issues with quantaq package
class MyQuantAQ(Manufacturer):
    @property
    def name(self):
        """
        Manufacturer name, as used as a section in the config file.
        """
        return "QuantAQ"

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
        self.final_data = cfg.getboolean(self.name, "final_data")

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
        raw = Template("timestamp,ge,$start;timestamp,lt,$end")
        self.query_string = raw.substitute(start=start_date, end=end_date)

        super().__init__(cfg)

    def connect(self):
        """
        Overrides super method as not using requests.
        """
        self.api_obj = quantaq.QuantAQ(self.api_token)
        # TODO Error handle
        return True

    def scrape_device(self, deviceID):
        """
        TODO
        """
        # try:
        data = self.api_obj.get_data(
            sn=deviceID,
            final_data=self.final_data,
            params=dict(filter=self.query_string),
        )
        # except quantaq.DataReadError:
        #    print("Cannot read data from QuantAQ's website")
        #    return None

        return data

    def process_device(self, deviceID):
        """
        TODO
        """
        pass
