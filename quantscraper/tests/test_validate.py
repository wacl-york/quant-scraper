"""
    test_validate.py
    ~~~~~~~~~~~~~~~~

    Unit tests for Manufacturer.validate().
"""

import unittest
import configparser
from string import Template
from unittest.mock import patch, MagicMock, Mock, call
from requests.exceptions import Timeout, HTTPError
from quantaq.baseapi import DataReadError
import quantscraper.manufacturers.Aeroqual as Aeroqual
import quantscraper.manufacturers.AQMesh as AQMesh
import quantscraper.manufacturers.Zephyr as Zephyr
import quantscraper.manufacturers.MyQuantAQ as MyQuantAQ
from quantscraper.utils import DataDownloadError
from quantscraper.tests.test_utils import build_mock_response

# Want to test that:
#    - Function parses timestamps correctly
#    - It returns the expected clean data
#    - Handles multiple error types (string, empty string, odd characters)


class TestAeroqual(unittest.TestCase):
    # TODO Should config be mocked too, or is it fair enough to use the example
    # config that is bundled with the source code?
    cfg = configparser.ConfigParser()
    cfg.read("example.ini")
    # TODO Set timestamp format, timestamp columns, and columns to validate
    cfg.set('Aeroqual', 'timestamp_format', '%%Y-%%m-%%d %%H:%%M')
    cfg.set('Aeroqual', 'timestamp_column', 'timestamp')
    cfg.set('Aeroqual', 'columns_to_validate', 'foo,bar,car')

    def test_success(self):
        data = [['not used', 'foo', 'timestamp', 'bar', 'unused', 'car'],
                ['5', '2', '2019-03-02 15:30', '23.9', '5.0', 'bar'],
                ['5', '2', '2019-03-02 15:31', '23.9', '5.0', '56.2'],
                ['5', '2.5', '2019-03-02 15:32', '-5.2', 'foo', '%%s'],
                ['', ' ', '2019-03-02 15:33', '', '', '1802'],
                ['5', '4.5', '2019-03-02 15:32:50', '', '5.0', 'bar'],
                ['2.8', '3.2', '', '-23.9', '9.7', '%format'],
                ['2.8', '3.2', ' ', '-23.9', '9.7', '%format'],
                ['23..8', '2str3', '2019-02-05 15:50', '90.2', '23', '  ']
               ]
        exp = [['2019-03-02-15:30', 'foo', 2],
               ['2019-03-02-15:30', 'bar', 23.9],
               ['2019-03-02-15:31', 'foo', 2],
               ['2019-03-02-15:31', 'bar', 23.9],
               ['2019-03-02-15:31', 'car', 56.2],
               ['2019-03-02-15:32', 'foo', 2.5],
               ['2019-03-02-15:32', 'bar', -5.2],
               ['2019-03-02-15:33', 'car', 1802],
               ['2019-03-02-15:50', 'bar', 90.2]
              ]

        aeroqual = Aeroqual.Aeroqual(self.cfg)
        try:
            res = aeroqual.validate_data(data)
            self.assertEqual(res, exp)
        except:
            self.fail("validate_data raised exception when it should have succeeded")


    # TODO Test no header

if __name__ == "__main__":
    unittest.main()
