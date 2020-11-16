"""
    test_log_device_status.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Unit tests for Manufacturer.log_device_status() methods.
"""

import unittest
from collections import defaultdict
from unittest.mock import Mock
from requests.exceptions import HTTPError
import quantscraper.manufacturers.Aeroqual as Aeroqual
import quantscraper.manufacturers.AQMesh as AQMesh
import quantscraper.manufacturers.Zephyr as Zephyr
import quantscraper.manufacturers.MyQuantAQ as MyQuantAQ
import quantscraper.manufacturers.AURN as AURN
import quantscraper.manufacturers.PurpleAir as PurpleAir
from quantscraper.utils import DataDownloadError
from utils import build_mock_response


class TestAeroqual(unittest.TestCase):
    # Will add tests back in once can reimplement this method
    cfg = defaultdict(str)
    fields = []
    aeroqual = Aeroqual.Aeroqual(cfg, fields)


class TestAQMesh(unittest.TestCase):
    # This method isn't currently implemented for AQMesh, so test it returns
    # an empty dict
    cfg = defaultdict(str)
    fields = []
    aqmesh = AQMesh.AQMesh(cfg, fields)

    def test_success(self):
        res = self.aqmesh.log_device_status("123")
        self.assertEqual(res, {})


class TestZephyr(unittest.TestCase):
    # This method isn't currently implemented for Zephyr, so test it returns
    # an empty dict
    cfg = defaultdict(str)
    fields = []
    zephyr = Zephyr.Zephyr(cfg, fields)

    def test_success(self):
        res = self.zephyr.log_device_status("123")
        self.assertEqual(res, {})


class TestMyQuantAQ(unittest.TestCase):
    # This method isn't currently implemented for QuantAQ, so test it returns
    # an empty dict
    cfg = defaultdict(str)
    fields = []
    myquantaq = MyQuantAQ.MyQuantAQ(cfg, fields)

    def test_success(self):
        res = self.myquantaq.log_device_status("foo")
        self.assertEqual(res, {})


class TestAURN(unittest.TestCase):
    # This method isn't currently implemented for AURN, so test it returns
    # an empty dict
    cfg = defaultdict(str)
    fields = []
    myaurn = AURN.AURN(cfg, fields)

    def test_success(self):
        res = self.myaurn.log_device_status("foo")
        self.assertEqual(res, {})


class TestPurpleAir(unittest.TestCase):
    # This method isn't currently implemented for PurpleAir, so test it returns
    # an empty dict
    cfg = defaultdict(str)
    fields = []
    mypa = PurpleAir.PurpleAir(cfg, fields)

    def test_success(self):
        res = self.mypa.log_device_status("foo")
        self.assertEqual(res, {})


if __name__ == "__main__":
    unittest.main()
