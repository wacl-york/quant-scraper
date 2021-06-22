"""
    quantscraper.manufacturers.EnvironmentalInstruments.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Concrete implementation of Manufacturer, representing the
    EnvironmentalInstruments air quality instrumentation device 
    manufacturer.

    This is just a sub-class of the AQMesh class as it interfaces using the
    same AirMonitors API.
    It has been subclassed to differentiate between these different manufacturers.
"""

from datetime import datetime, time
import json
import os
import requests as re
import pandas as pd
from quantscraper.manufacturers.AQMesh import AQMesh
from quantscraper.utils import LoginError, DataDownloadError, DataParseError


class EnvironmentalInstruments(AQMesh):
    """
    Inherits all attributes and methods from EnvironmentalInstruments as
    these 2 copmanies use the same AirMonitors API.
    """

    name = "EnvironmentalInstruments"
