"""
    quantscraper.manufacturers.ClarityGCRF.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Concrete implementation of Manufacturer, representing the Clarity air
    quality instrumentation device manufacturer.
    This class represents the 5 Clarity devices that were ordered as part of the
    GCRF project.
"""

from datetime import datetime, time
import json
import os
import requests as re
import pandas as pd
from quantscraper.manufacturers.Manufacturer import Manufacturer
from quantscraper.manufacturers.Clarity import Clarity
from quantscraper.utils import LoginError, DataDownloadError, DataParseError


class ClarityGCRF(Clarity):
    """
    Inherits attributes and methods from Clarity along with providing
    implementations of:
        - connect()
        - scrape_device()
        - parse_to_csv()
    """

    name = "ClarityGCRF"

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
            "x-api-key": os.environ["CLARITYGCRF_API_KEY"],
            "Accept-Encoding": "gzip",
        }

        Manufacturer.__init__(self, cfg, fields)
