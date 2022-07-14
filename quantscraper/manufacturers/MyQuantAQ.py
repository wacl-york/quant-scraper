"""
    quantscraper.manufacturers.MyQuantAQ.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Concrete implementation of Manufacturer, representing the MyQuantAQ air
    quality instrumentation device manufacturer.

    The reason why 'My' prepends the module and class name is to avoid
    any conflict with QuantAQ's own API, which has a QuantAQ class.
"""

from datetime import timedelta
from string import Template
import os
import requests as re
import quantaq
from quantscraper.manufacturers.Manufacturer import Manufacturer
from quantscraper.utils import (
    LoginError,
    DataDownloadError,
    DataParseError,
    flatten_2d_dict,
)
import pandas as pd


class MyQuantAQ(Manufacturer):
    """
    Inherits attributes and methods from Manufacturer along with providing
    implementations of:
        - connect()
        - scrape_device()
        - parse_to_csv()

    The reason why 'My' prepends the module and class name is to avoid
    any conflict with QuantAQ's own API, which has a QuantAQ class.
    """

    name = "QuantAQ"

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
        self.api_obj = None
        self.api_token = os.environ["QUANTAQ_API_TOKEN"]

        # This would be more easily saved as a dict as that's how it gets used
        # later, but the quantaq package does some funny dict updating by
        # reference that modifies the dict from my environment
        self.query_string = Template("timestamp,ge,${start};timestamp,lt,${end}")

        super().__init__(cfg, fields)

    def connect(self):
        """
        Establishes a connection to the QuantAQ API.

        Creates an instance of the QuantAQ API class using the stored
        API token, then checks the authentication was successful by attempting
        to run a basic query to get the account information.

        Args:
            - None.

        Returns:
            None, although a handle to the API is stored in the instance
            attribute 'api_obj'.
        """
        self.api_obj = quantaq.QuantAQ(self.api_token)
        # Test connection by running basic query
        try:
            self.api_obj.get_account()
        except (
            quantaq.baseapi.DataReadError,
            re.exceptions.ConnectionError,
            quantaq.NotFoundError,
        ) as ex:
            raise LoginError(f"Could not connect to quantaq API.\n{ex}") from None

    def log_device_status(self, device_id):
        """
        Scrapes information about a device's operating condition.

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

        QuantAQ provide both 'raw' and 'final' data through their API.
        The raw data is measured at the sensor voltage level, while the final
        data has had their internal processing pipeline applied to convert
        these values into standard concentration measurements.

        Both the raw and final data are stored from this call.

        Args:
            - device_id (str): The ID used by the website to refer to the
                device.
            - start (date): The start of the scraping window.
            - end (date): The end of the scraping window.

        Returns:
            A dict with 2 attributes: 'raw' and 'final', holding the raw and
            final data respectively from the API calls.
            Each of these datasets are stored as lists of dicts, with each list
            entry corresponding to a unique time-point.
        """
        # Load start and end scraping datetimes
        start_date = start.strftime("%Y-%m-%d")
        # Notice how we add on 1 day here.
        # Although there is a "less than or equal to" filter,
        # if you use ">= start_date and <= end_date" where start_date=end_date,
        # i.e. the common scenario in our usage, then it raises an error.
        # The solution is to add a day onto the end_date,
        # and use < rather than <=
        end_date = (end + timedelta(days=1)).strftime("%Y-%m-%d")

        query = self.query_string.substitute(start=start_date, end=end_date)

        try:
            raw = self.api_obj.get_data(
                sn=device_id, final_data=False, params=dict(filter=query),
            )
        except (quantaq.baseapi.DataReadError, re.exceptions.ConnectionError) as ex:
            raise DataDownloadError(
                "Cannot read data from QuantAQ's website:\n{}".format(ex)
            ) from None
        try:
            final = self.api_obj.get_data(
                sn=device_id, final_data=True, params=dict(filter=query),
            )
        except (quantaq.baseapi.DataReadError, re.exceptions.ConnectionError) as ex:
            raise DataDownloadError(
                "Cannot read data from QuantAQ's website:\n{}".format(ex)
            ) from None

        if len(raw) == 0 and len(final) == 0:
            raise DataDownloadError("No available data in the downloaded file.")

        data = {"raw": raw, "final": final}
        return data

    def parse_to_csv(self, raw_data):
        """
        Parses the raw data into a 2D list format.

        As returned from the scrape_device() method, the input
        raw data is a dict with 2 attributes: 'raw' and 'final'.
        Since the purpose of this project is to generate the cleaned and
        validated air quality measurements, the 'final' dataset is used in
        this method.

        The 'final' data is stored as a list, with each entry corresponding
        to a unique time-point. A dict is stored at each entry, mapping
        {measurand: value}.

        The key considerations here is that firstly not all of these measurands
        are recorded values of interest: the 'url' and 'sn' entries provide
        irrelevant metadata and so are discarded.
        Secondly, in each time-point's dict, there is an additional dict
        stored in the 'geo' attribute, which contains a secondary mapping
        between 'lat' and 'lon' and their respective values.
        It would be easier if these 'lat' and 'lon' values were stored in the
        same level as the other measurands.

        Currently the code explicitly extracts the 'lat' and 'lon'
        measurements from within their secondary dict.
        It could be made more generalizable by looking for the presence of
        any other secondary dicts and extracting their contents automatically.

        Args:
            - raw_data (dict): The raw data, see above for documentation about
                how this is stored and any considerations when parsing it.
        Returns:
            A 2D list representing the data in a tabular format, so that each
            row corresponds to a unique time-point and each column holds a
            measurand.
        """
        raw_data = raw_data["final"]
        nrows = len(raw_data)
        if nrows < 1:
            raise DataParseError("No data found.")

        flattened = [flatten_2d_dict(record) for record in raw_data]

        df = pd.DataFrame(flattened)
        # I'm only dropping url as I've observed for our devices we have
        # duplicated measurements with different urls. It's not a problem if url
        # field isn't present
        # Edit 2022-07-14: The Gas and PM fields have been added around the
        # 12th July and caused the scraper to stop working. They are parameters
        # related to the calibration model and so don't need to be included in
        # the clean data
        df.drop(columns=["url", "gas", "pm"], inplace=True, errors="ignore")

        clean_data = [df.columns.tolist()] + df.values.tolist()

        return clean_data
