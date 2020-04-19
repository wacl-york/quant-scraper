"""
    test_validate.py
    ~~~~~~~~~~~~~~~~

    Unit tests for Manufacturer.validate().
"""

import unittest
import configparser
import quantscraper.manufacturers.Aeroqual as Aeroqual
import quantscraper.utils as utils
from test_utils import build_mock_response


class TestIsFloat(unittest.TestCase):
    # Test utils.is_float() function

    def test_float(self):
        self.assertTrue(utils.is_float("5.23"))

    def test_exponent(self):
        self.assertTrue(utils.is_float("2e2"))

    def test_exponent2(self):
        self.assertTrue(utils.is_float("-1.5e5"))

    def test_exponent_inf(self):
        self.assertFalse(utils.is_float("-1.5e5000"))

    def test_negative_float(self):
        self.assertTrue(utils.is_float("-8.03"))

    def test_int(self):
        self.assertTrue(utils.is_float("83"))

    def test_negative_int(self):
        self.assertTrue(utils.is_float("-232"))

    def test_0_int(self):
        self.assertTrue(utils.is_float("0"))

    def test_0_float(self):
        self.assertTrue(utils.is_float("0.0"))

    def test_negative_0_int(self):
        self.assertTrue(utils.is_float("-0"))

    def test_negative_0_float(self):
        self.assertTrue(utils.is_float("-0.0"))

    def test_inf(self):
        self.assertFalse(utils.is_float("Inf"))

    def test_inf2(self):
        self.assertFalse(utils.is_float("INF"))

    def test_inf3(self):
        self.assertFalse(utils.is_float("INFINITY"))

    def test_inf4(self):
        self.assertFalse(utils.is_float("inf"))

    def test_negative_inf(self):
        self.assertFalse(utils.is_float("-Inf"))

    def test_negative_inf2(self):
        self.assertFalse(utils.is_float("-INF"))

    def test_negative_inf3(self):
        self.assertFalse(utils.is_float("-INFINITY"))

    def test_negative_inf4(self):
        self.assertFalse(utils.is_float("-inf"))

    def test_nan(self):
        self.assertFalse(utils.is_float("Nan"))

    def test_nan2(self):
        self.assertFalse(utils.is_float("NAN"))

    def test_nan3(self):
        self.assertFalse(utils.is_float("NaN"))

    def test_nan4(self):
        self.assertFalse(utils.is_float("nan"))

    def test_negative_nan(self):
        self.assertFalse(utils.is_float("-Nan"))

    def test_negative_nan2(self):
        self.assertFalse(utils.is_float("-NAN"))

    def test_negative_nan3(self):
        self.assertFalse(utils.is_float("-NaN"))

    def test_negative_nan4(self):
        self.assertFalse(utils.is_float("-nan"))

    def test_special_char(self):
        self.assertFalse(utils.is_float("%%1"))

    def test_special_char2(self):
        self.assertFalse(utils.is_float("1%"))

    def test_special_char3(self):
        self.assertFalse(utils.is_float("{}.format(2)"))

    def test_none(self):
        self.assertFalse(utils.is_float("None"))

    def test_false(self):
        self.assertFalse(utils.is_float("False"))

    def test_false2(self):
        self.assertFalse(utils.is_float("false"))

    def test_true(self):
        self.assertFalse(utils.is_float("True"))

    def test_true2(self):
        self.assertFalse(utils.is_float("true"))


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
    cfg.set("Aeroqual", "timestamp_format", "%%Y-%%m-%%d %%H:%%M")
    cfg.set("Aeroqual", "timestamp_column", "timestamp")
    cfg.set("Aeroqual", "columns_to_validate", "foo,bar,car")
    cfg.set("Aeroqual", "column_labels", "foo,bar,car")
    cfg.set("Aeroqual", "scaling_factors", "1,1,1")

    def test_success(self):
        data = [
            ["not used", "foo", "timestamp", "bar", "unused", "car"],
            ["5", "2", "2019-03-02 15:30", "23.9", "5.0", "bar"],
            ["5", "2", "2019-03-02 15:31", "23.9", "5.0", "56.2"],
            ["5", "2.5", "2019-03-02 15:32", "-5.2", "foo", "%%s"],
            ["", " ", "2019-05-21 15:33", "", "", "1802"],
            ["5", "4.5", "2019-03-02 15:32:50", "", "5.0", "bar"],
            ["2.8", "3.2", "", "-23.9", "9.7", "%format"],
            ["2.8", "3.2", " ", "-23.9", "9.7", "%format"],
            ["2.8", "3.2", "2018-02-31 18:00", "23.2", "9.7", "28.9"],
            ["23..8", "2str3", "2040-12-31 00:28", "90.2", "23", "  "],
        ]
        exp = [
            ["timestamp", "measurand", "value"],
            ["2019-03-02 15:30:00", "foo", 2.0],
            ["2019-03-02 15:30:00", "bar", 23.9],
            ["2019-03-02 15:31:00", "foo", 2.0],
            ["2019-03-02 15:31:00", "bar", 23.9],
            ["2019-03-02 15:31:00", "car", 56.2],
            ["2019-03-02 15:32:00", "foo", 2.5],
            ["2019-03-02 15:32:00", "bar", -5.2],
            ["2019-05-21 15:33:00", "car", 1802.0],
            ["2040-12-31 00:28:00", "bar", 90.2],
        ]

        aeroqual = Aeroqual.Aeroqual(self.cfg)
        try:
            res, _ = aeroqual.validate_data(data)
            self.assertEqual(res, exp)
        except:
            self.fail("validate_data raised exception when it should have succeeded")

    def test_special_chars(self):
        # Test NaN, exponent notation, Inf
        # Should be no floats here, except for exponent 1e5. 20e888232 = Inf
        data = [
            ["not used", "foo", "timestamp", "bar", "unused", "car"],
            ["5", "Inf", "2019-03-02 15:30", "NaN", "5.0", "1e5"],
            ["5", "-Inf", "2019-03-02 15:31", "NAN", "5.0", "20e888232"],
            ["5", "INF", "2019-03-02 15:32", "NAN", "5.0", "bar"],
            ["5", "Inf", "2019-03-02 15:33", "NaN", "5.0", "bar"],
        ]
        exp = [
            ["timestamp", "measurand", "value"],
            ["2019-03-02 15:30:00", "car", 1e5],
        ]

        aeroqual = Aeroqual.Aeroqual(self.cfg)
        try:
            res, _ = aeroqual.validate_data(data)
            self.assertEqual(res, exp)
        except:
            self.fail("validate_data raised exception when it should have succeeded")

    def test_no_header(self):
        data = [
            ["5", "2", "2019-03-02 15:30", "23.9", "5.0", "bar"],
            ["5", "2", "2019-03-02 15:31", "23.9", "5.0", "56.2"],
            ["5", "2.5", "2019-03-02 15:32", "-5.2", "foo", "%%s"],
            ["", " ", "2019-05-21 15:33", "", "", "1802"],
            ["5", "4.5", "2019-03-02 15:32:50", "", "5.0", "bar"],
            ["2.8", "3.2", "", "-23.9", "9.7", "%format"],
            ["2.8", "3.2", " ", "-23.9", "9.7", "%format"],
            ["2.8", "3.2", "2018-02-31 18:00", "23.2", "9.7", "28.9"],
            ["23..8", "2str3", "2040-12-31 00:28", "90.2", "23", "  "],
        ]

        aeroqual = Aeroqual.Aeroqual(self.cfg)
        with self.assertRaises(utils.ValidateDataError):
            res, _ = aeroqual.validate_data(data)

    def test_no_data(self):
        data = [
            ["not used", "foo", "timestamp", "bar", "unused", "car"],
        ]

        aeroqual = Aeroqual.Aeroqual(self.cfg)
        try:
            res, _ = aeroqual.validate_data(data)
            exp = [["timestamp", "measurand", "value"]]
            self.assertEqual(res, exp)
        except:
            self.fail("validate_data raised exception when it should have succeeded")

    def test_empty_list(self):
        data = []

        aeroqual = Aeroqual.Aeroqual(self.cfg)
        with self.assertRaises(utils.ValidateDataError):
            res, _ = aeroqual.validate_data(data)

    def test_None(self):
        data = None
        aeroqual = Aeroqual.Aeroqual(self.cfg)
        with self.assertRaises(utils.ValidateDataError):
            res, _ = aeroqual.validate_data(data)

    def test_no_timestamp_col(self):
        data = [
            ["not used", "foo", "bar", "unused", "car"],
            ["5", "2", "2019-03-02 15:30", "23.9", "5.0", "bar"],
            ["5", "2", "2019-03-02 15:31", "23.9", "5.0", "56.2"],
            ["5", "2.5", "2019-03-02 15:32", "-5.2", "foo", "%%s"],
            ["", " ", "2019-05-21 15:33", "", "", "1802"],
            ["5", "4.5", "2019-03-02 15:32:50", "", "5.0", "bar"],
            ["2.8", "3.2", "", "-23.9", "9.7", "%format"],
            ["2.8", "3.2", " ", "-23.9", "9.7", "%format"],
            ["2.8", "3.2", "2018-02-31 18:00", "23.2", "9.7", "28.9"],
            ["23..8", "2str3", "2040-12-31 00:28", "90.2", "23", "  "],
        ]
        aeroqual = Aeroqual.Aeroqual(self.cfg)
        with self.assertRaises(utils.ValidateDataError):
            res, _ = aeroqual.validate_data(data)

    def test_missing_measurands(self):
        # Here are asking for measurands that aren't in the raw data. Should
        # pass as very well could have situation where different devices
        # from same manufacturer have different sensor equipped
        cfg_copy = utils.copy_object(self.cfg)
        cfg_copy.set("Aeroqual", "columns_to_validate", "foo,bar,car,donkey")
        cfg_copy.set("Aeroqual", "column_labels", "foo,bar,car,donkey")
        cfg_copy.set("Aeroqual", "scaling_factors", "1,1,1,1")
        data = [
            ["not used", "foo", "timestamp", "bar", "unused", "car"],
            ["5", "2", "2019-03-02 15:30", "23.9", "5.0", "bar"],
            ["5", "2", "2019-03-02 15:31", "23.9", "5.0", "56.2"],
            ["5", "2.5", "2019-03-02 15:32", "-5.2", "foo", "%%s"],
            ["", " ", "2019-05-21 15:33", "", "", "1802"],
            ["5", "4.5", "2019-03-02 15:32:50", "", "5.0", "bar"],
            ["2.8", "3.2", "", "-23.9", "9.7", "%format"],
            ["2.8", "3.2", " ", "-23.9", "9.7", "%format"],
            ["2.8", "3.2", "2018-02-31 18:00", "23.2", "9.7", "28.9"],
            ["23..8", "2str3", "2040-12-31 00:28", "90.2", "23", "  "],
        ]
        exp = [
            ["timestamp", "measurand", "value"],
            ["2019-03-02 15:30:00", "foo", 2.0],
            ["2019-03-02 15:30:00", "bar", 23.9],
            ["2019-03-02 15:31:00", "foo", 2.0],
            ["2019-03-02 15:31:00", "bar", 23.9],
            ["2019-03-02 15:31:00", "car", 56.2],
            ["2019-03-02 15:32:00", "foo", 2.5],
            ["2019-03-02 15:32:00", "bar", -5.2],
            ["2019-05-21 15:33:00", "car", 1802.0],
            ["2040-12-31 00:28:00", "bar", 90.2],
        ]

        aeroqual = Aeroqual.Aeroqual(cfg_copy)
        try:
            res, _ = aeroqual.validate_data(data)
            self.assertEqual(res, exp)
        except:
            self.fail("validate_data raised exception when it should have succeeded")

    def test_invalid_timestamp_format(self):
        # If forget to add the %%s, then timestamps won't be parsed and thus
        # will get empty output
        cfg_copy = utils.copy_object(self.cfg)
        cfg_copy.set("Aeroqual", "timestamp_format", "Y-m-d H:M")
        data = [
            ["not used", "foo", "timestamp", "bar", "unused", "car"],
            ["5", "2", "2019-03-02 15:30", "23.9", "5.0", "bar"],
            ["5", "2", "2019-03-02 15:31", "23.9", "5.0", "56.2"],
            ["5", "2.5", "2019-03-02 15:32", "-5.2", "foo", "%%s"],
            ["", " ", "2019-05-21 15:33", "", "", "1802"],
            ["5", "4.5", "2019-03-02 15:32:50", "", "5.0", "bar"],
            ["2.8", "3.2", "", "-23.9", "9.7", "%format"],
            ["2.8", "3.2", " ", "-23.9", "9.7", "%format"],
            ["2.8", "3.2", "2018-02-31 18:00", "23.2", "9.7", "28.9"],
            ["23..8", "2str3", "2040-12-31 00:28", "90.2", "23", "  "],
        ]
        aeroqual = Aeroqual.Aeroqual(cfg_copy)
        try:
            res, _ = aeroqual.validate_data(data)
            exp = [["timestamp", "measurand", "value"]]
            self.assertEqual(res, exp)
        except:
            self.fail("validate_data raised exception when it should have succeeded")

    def test_invalid_timestamp_format2(self):
        # If ask for wrong format, i.e. %y (00, 01) rather than %Y (2000, 2001),
        # then should also find no valid timestamps
        cfg_copy = utils.copy_object(self.cfg)
        cfg_copy.set("Aeroqual", "timestamp_format", "%%y-%%m-%%d %%H:%%M")
        data = [
            ["not used", "foo", "timestamp", "bar", "unused", "car"],
            ["5", "2", "2019-03-02 15:30", "23.9", "5.0", "bar"],
            ["5", "2", "2019-03-02 15:31", "23.9", "5.0", "56.2"],
            ["5", "2.5", "2019-03-02 15:32", "-5.2", "foo", "%%s"],
            ["", " ", "2019-05-21 15:33", "", "", "1802"],
            ["5", "4.5", "2019-03-02 15:32:50", "", "5.0", "bar"],
            ["2.8", "3.2", "", "-23.9", "9.7", "%format"],
            ["2.8", "3.2", " ", "-23.9", "9.7", "%format"],
            ["2.8", "3.2", "2018-02-31 18:00", "23.2", "9.7", "28.9"],
            ["23..8", "2str3", "2040-12-31 00:28", "90.2", "23", "  "],
        ]
        aeroqual = Aeroqual.Aeroqual(cfg_copy)
        try:
            res, _ = aeroqual.validate_data(data)
            exp = [["timestamp", "measurand", "value"]]
            self.assertEqual(res, exp)
        except:
            self.fail("validate_data raised exception when it should have succeeded")


if __name__ == "__main__":
    unittest.main()
