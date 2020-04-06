"""
    test_validate.py
    ~~~~~~~~~~~~~~~~

    Unit tests for Manufacturer.validate().
"""

import unittest
import pickle
import configparser
from string import Template
from unittest.mock import patch, MagicMock, Mock, call
from requests.exceptions import Timeout, HTTPError
from quantaq.baseapi import DataReadError
import quantscraper.manufacturers.Aeroqual as Aeroqual
import quantscraper.manufacturers.AQMesh as AQMesh
import quantscraper.manufacturers.Zephyr as Zephyr
import quantscraper.manufacturers.MyQuantAQ as MyQuantAQ
from quantscraper.utils import ValidateDataError
from quantscraper.tests.test_utils import build_mock_response

# Want to test that:
#    - Function parses timestamps correctly
#    - It returns the expected clean data
#    - Handles multiple error types (string, empty string, odd characters)

def copy_config(input):
    """
    Function to deep copy config parser object so can make changes to test
    config without polluting the class namespace.

    This pickle method should work for any Python 3 object.

    Args:
        input (ConfigParser): input ConfigParser object.

    Returns:
        A deep copy of 'input', a second ConfigParser object.
    """
    pickle_in = pickle.dumps(input)
    pickle_out = pickle.loads(pickle_in)
    return pickle_out


class TestValidate(unittest.TestCase):

    # Although Aeroqual is used for this test, it doesn't matter which
    # Manufacturer subclass is chosen, as the validate_data() method doesn't
    # depend on any instance attributes except for timestamp format,
    # timestamp_column, and columns_to_validate, all of which can be set through
    # the configparser to test a range of inputs. 
    # The input data type should be uniformly CSV, as this validate_data method 
    # is called after parse_to_csv has been run.

    # TODO Should config be mocked too, or is it fair enough to use the example
    # config that is bundled with the source code?
    cfg = configparser.ConfigParser()
    cfg.read("example.ini")
    # Set timestamp format, timestamp columns, and columns to validate
    cfg.set('Aeroqual', 'timestamp_format', '%%Y-%%m-%%d %%H:%%M')
    cfg.set('Aeroqual', 'timestamp_column', 'timestamp')
    cfg.set('Aeroqual', 'columns_to_validate', 'foo,bar,car')

    def test_success(self):
        data = [['not used', 'foo', 'timestamp', 'bar', 'unused', 'car'],
                ['5', '2', '2019-03-02 15:30', '23.9', '5.0', 'bar'],
                ['5', '2', '2019-03-02 15:31', '23.9', '5.0', '56.2'],
                ['5', '2.5', '2019-03-02 15:32', '-5.2', 'foo', '%%s'],
                ['', ' ', '2019-05-21 15:33', '', '', '1802'],
                ['5', '4.5', '2019-03-02 15:32:50', '', '5.0', 'bar'],
                ['2.8', '3.2', '', '-23.9', '9.7', '%format'],
                ['2.8', '3.2', ' ', '-23.9', '9.7', '%format'],
                ['2.8', '3.2', '2018-02-31 18:00', '23.2', '9.7', '28.9'],
                ['23..8', '2str3', '2040-12-31 00:28', '90.2', '23', '  ']
               ]
        exp = [['2019-03-02 15:30:00', 'foo', 2.0],
               ['2019-03-02 15:30:00', 'bar', 23.9],
               ['2019-03-02 15:31:00', 'foo', 2.0],
               ['2019-03-02 15:31:00', 'bar', 23.9],
               ['2019-03-02 15:31:00', 'car', 56.2],
               ['2019-03-02 15:32:00', 'foo', 2.5],
               ['2019-03-02 15:32:00', 'bar', -5.2],
               ['2019-05-21 15:33:00', 'car', 1802.0],
               ['2040-12-31 00:28:00', 'bar', 90.2]
              ]

        aeroqual = Aeroqual.Aeroqual(self.cfg)
        try:
            res = aeroqual.validate_data(data)
            self.assertEqual(res, exp)
        except:
            self.fail("validate_data raised exception when it should have succeeded")

    def test_no_header(self):
        data = [
                ['5', '2', '2019-03-02 15:30', '23.9', '5.0', 'bar'],
                ['5', '2', '2019-03-02 15:31', '23.9', '5.0', '56.2'],
                ['5', '2.5', '2019-03-02 15:32', '-5.2', 'foo', '%%s'],
                ['', ' ', '2019-05-21 15:33', '', '', '1802'],
                ['5', '4.5', '2019-03-02 15:32:50', '', '5.0', 'bar'],
                ['2.8', '3.2', '', '-23.9', '9.7', '%format'],
                ['2.8', '3.2', ' ', '-23.9', '9.7', '%format'],
                ['2.8', '3.2', '2018-02-31 18:00', '23.2', '9.7', '28.9'],
                ['23..8', '2str3', '2040-12-31 00:28', '90.2', '23', '  ']
               ]

        aeroqual = Aeroqual.Aeroqual(self.cfg)
        with self.assertRaises(ValidateDataError):
            res = aeroqual.validate_data(data)

    def test_no_data(self):
        data = [['not used', 'foo', 'timestamp', 'bar', 'unused', 'car'],
               ]

        aeroqual = Aeroqual.Aeroqual(self.cfg)
        try:
            res = aeroqual.validate_data(data)
            exp = []
            self.assertEqual(res, exp)
        except:
            self.fail("validate_data raised exception when it should have succeeded")

    def test_empty_list(self):
        data = [
               ]

        aeroqual = Aeroqual.Aeroqual(self.cfg)
        with self.assertRaises(ValidateDataError):
            res = aeroqual.validate_data(data)

    def test_None(self):
        data = None
        aeroqual = Aeroqual.Aeroqual(self.cfg)
        with self.assertRaises(ValidateDataError):
            res = aeroqual.validate_data(data)

    def test_no_timestamp_col(self):
        data = [['not used', 'foo', 'bar', 'unused', 'car'],
                ['5', '2', '2019-03-02 15:30', '23.9', '5.0', 'bar'],
                ['5', '2', '2019-03-02 15:31', '23.9', '5.0', '56.2'],
                ['5', '2.5', '2019-03-02 15:32', '-5.2', 'foo', '%%s'],
                ['', ' ', '2019-05-21 15:33', '', '', '1802'],
                ['5', '4.5', '2019-03-02 15:32:50', '', '5.0', 'bar'],
                ['2.8', '3.2', '', '-23.9', '9.7', '%format'],
                ['2.8', '3.2', ' ', '-23.9', '9.7', '%format'],
                ['2.8', '3.2', '2018-02-31 18:00', '23.2', '9.7', '28.9'],
                ['23..8', '2str3', '2040-12-31 00:28', '90.2', '23', '  ']
               ]
        aeroqual = Aeroqual.Aeroqual(self.cfg)
        with self.assertRaises(ValidateDataError):
            res = aeroqual.validate_data(data)

    def test_missing_measurands(self):
        # Here are asking for measurands that aren't in the raw data. Should
        # pass as very well could have situation where different devices
        # from same manufacturer have different sensor equipped
        cfg_copy = copy_config(self.cfg)
        cfg_copy.set('Aeroqual', 'columns_to_validate', 'foo,bar,car,donkey')
        data = [['not used', 'foo', 'timestamp', 'bar', 'unused', 'car'],
                ['5', '2', '2019-03-02 15:30', '23.9', '5.0', 'bar'],
                ['5', '2', '2019-03-02 15:31', '23.9', '5.0', '56.2'],
                ['5', '2.5', '2019-03-02 15:32', '-5.2', 'foo', '%%s'],
                ['', ' ', '2019-05-21 15:33', '', '', '1802'],
                ['5', '4.5', '2019-03-02 15:32:50', '', '5.0', 'bar'],
                ['2.8', '3.2', '', '-23.9', '9.7', '%format'],
                ['2.8', '3.2', ' ', '-23.9', '9.7', '%format'],
                ['2.8', '3.2', '2018-02-31 18:00', '23.2', '9.7', '28.9'],
                ['23..8', '2str3', '2040-12-31 00:28', '90.2', '23', '  ']
               ]
        exp = [['2019-03-02 15:30:00', 'foo', 2.0],
               ['2019-03-02 15:30:00', 'bar', 23.9],
               ['2019-03-02 15:31:00', 'foo', 2.0],
               ['2019-03-02 15:31:00', 'bar', 23.9],
               ['2019-03-02 15:31:00', 'car', 56.2],
               ['2019-03-02 15:32:00', 'foo', 2.5],
               ['2019-03-02 15:32:00', 'bar', -5.2],
               ['2019-05-21 15:33:00', 'car', 1802.0],
               ['2040-12-31 00:28:00', 'bar', 90.2]
              ]

        aeroqual = Aeroqual.Aeroqual(cfg_copy)
        try:
            res = aeroqual.validate_data(data)
            self.assertEqual(res, exp)
        except:
            self.fail("validate_data raised exception when it should have succeeded")

    def test_invalid_timestamp_format(self):
        # If forget to add the %%s, then timestamps won't be parsed and thus
        # will get empty output
        cfg_copy = copy_config(self.cfg)
        cfg_copy.set('Aeroqual', 'timestamp_format', 'Y-m-d H:M')
        data = [['not used', 'foo', 'timestamp', 'bar', 'unused', 'car'],
                ['5', '2', '2019-03-02 15:30', '23.9', '5.0', 'bar'],
                ['5', '2', '2019-03-02 15:31', '23.9', '5.0', '56.2'],
                ['5', '2.5', '2019-03-02 15:32', '-5.2', 'foo', '%%s'],
                ['', ' ', '2019-05-21 15:33', '', '', '1802'],
                ['5', '4.5', '2019-03-02 15:32:50', '', '5.0', 'bar'],
                ['2.8', '3.2', '', '-23.9', '9.7', '%format'],
                ['2.8', '3.2', ' ', '-23.9', '9.7', '%format'],
                ['2.8', '3.2', '2018-02-31 18:00', '23.2', '9.7', '28.9'],
                ['23..8', '2str3', '2040-12-31 00:28', '90.2', '23', '  ']
               ]
        aeroqual = Aeroqual.Aeroqual(cfg_copy)
        try:
            res = aeroqual.validate_data(data)
            exp = []
            self.assertEqual(res, exp)
        except:
            self.fail("validate_data raised exception when it should have succeeded")

    def test_invalid_timestamp_format2(self):
        # If ask for wrong format, i.e. %y (00, 01) rather than %Y (2000, 2001),
        # then should also find no valid timestamps
        cfg_copy = copy_config(self.cfg)
        cfg_copy.set('Aeroqual', 'timestamp_format', '%%y-%%m-%%d %%H:%%M')
        data = [['not used', 'foo', 'timestamp', 'bar', 'unused', 'car'],
                ['5', '2', '2019-03-02 15:30', '23.9', '5.0', 'bar'],
                ['5', '2', '2019-03-02 15:31', '23.9', '5.0', '56.2'],
                ['5', '2.5', '2019-03-02 15:32', '-5.2', 'foo', '%%s'],
                ['', ' ', '2019-05-21 15:33', '', '', '1802'],
                ['5', '4.5', '2019-03-02 15:32:50', '', '5.0', 'bar'],
                ['2.8', '3.2', '', '-23.9', '9.7', '%format'],
                ['2.8', '3.2', ' ', '-23.9', '9.7', '%format'],
                ['2.8', '3.2', '2018-02-31 18:00', '23.2', '9.7', '28.9'],
                ['23..8', '2str3', '2040-12-31 00:28', '90.2', '23', '  ']
               ]
        aeroqual = Aeroqual.Aeroqual(cfg_copy)
        try:
            res = aeroqual.validate_data(data)
            exp = []
            self.assertEqual(res, exp)
        except:
            self.fail("validate_data raised exception when it should have succeeded")


if __name__ == "__main__":
    unittest.main()
