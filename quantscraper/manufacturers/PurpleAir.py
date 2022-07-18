"""
    quantscraper.manufacturers.PurpleAir.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Concrete implementation of Manufacturer, representing the PurpleAir air
    quality instrumentation device manufacturer.
"""

import csv
import logging
from datetime import datetime, timedelta, time
import os
from string import Template
import requests as re
from quantscraper.manufacturers.Manufacturer import Manufacturer
from quantscraper.utils import LoginError, DataDownloadError, DataParseError


class PurpleAir(Manufacturer):
    """
    Inherits attributes and methods from Manufacturer along with providing
    implementations of:
        - connect()
        - scrape_device()
        - parse_to_csv()
    """

    name = "PurpleAir"

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
        super().__init__(cfg, fields)

    def connect(self):
        """
        This function is not implemented for PurpleAir as we do not have a
        network connection to our devices.

        Args:
            - None.

        Returns:
            None
        """
        pass

    def log_device_status(self, device_id):
        """
        This function is not implemented for PurpleAir as we do not have a
        network connection to our devices.

        Args:
            - device_id (str): The ID used by the website to refer to the
                device.

        Returns:
            None
        """
        params = {}
        return params

    def scrape_device(self, device_id, start, end):
        """
        This function is not implemented for PurpleAir as we do not have a
        network connection to our devices.

        Args:
            - device_id (str): The ID used by the website to refer to the
                device.
            - start (date): The start of the scraping window.
            - end (date): The end of the scraping window.

        Returns:
            None
        """
        pass

    def parse_to_csv(self, raw_data):
        """
        Parses the raw data into a 2D list format.

        The data already comes in a CSV format \r\n line separators and comma
        field delimiters.

        Args:
            - raw_data (str): The raw data is stored in as a CSV formatted as a
                string.

        Returns:
            A 2D list representing the data in a tabular format, so that each
            row corresponds to a unique time-point and each column holds a
            measurand.
        """
        # Parse into csv using inbuilt csv module
        raw_lines = raw_data.rstrip().split("\n")
        reader = csv.reader(raw_lines, delimiter=",")

        try:
            data = list(reader)
        except csv.Error as ex:
            raise DataParseError(f"Error when parsing the file: {ex}") from None

        # Remove empty lines
        data = [row for row in data if len(row) > 0]

        if len(data) == 0:
            raise DataParseError("Have no rows of data available.")

        # Remove 'gas' from the header as this field isn't used
        if data[0][-1] == "gas":
            data[0] = data[0][:-1]

        # Ditch rows that have different number of fields to those in header
        data = [row for row in data if len(row) == len(data[0])]

        return data
