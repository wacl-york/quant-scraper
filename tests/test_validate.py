"""
    test_validate.py
    ~~~~~~~~~~~~~~~~

    Unit tests for Manufacturer.validate().
"""

from collections import defaultdict
import unittest
import quantscraper.manufacturers.Aeroqual as Aeroqual
import quantscraper.utils as utils


class TestValidate(unittest.TestCase):

    # Although Aeroqual is used for this test, it doesn't matter which
    # Manufacturer subclass is chosen, as the validate_data() method doesn't
    # depend on any instance attributes except for timestamp format,
    # timestamp_column, and columns_to_validate, all of which can be set through
    # the configparser to test a range of inputs.
    # The input data type should be uniformly CSV, as this validate_data method
    # is called after parse_to_csv has been run.

    cfg = defaultdict(str)
    cfg["timestamp_column"] = "timestamp"
    cfg["timestamp_format"] = "%Y-%m-%d %H:%M"
    fields = [
        {"id": "foo", "webid": "foo", "scale": 1},
        {"id": "bar", "webid": "bar", "scale": 1},
        {"id": "car", "webid": "car", "scale": 1},
    ]

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
        fmt = "%Y-%m-%d %H:%M:%S"
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

        aeroqual = Aeroqual.Aeroqual(self.cfg, self.fields)
        res, _ = aeroqual.validate_data(data, fmt)
        self.assertCountEqual(res, exp)

    def test_timestamp_format(self):
        # Testing a different output datetime format
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
        fmt = "%Y-%m-%dT %H:%M:%SZ+1"
        exp = [
            ["timestamp", "measurand", "value"],
            ["2019-03-02T 15:30:00Z+1", "foo", 2.0],
            ["2019-03-02T 15:30:00Z+1", "bar", 23.9],
            ["2019-03-02T 15:31:00Z+1", "foo", 2.0],
            ["2019-03-02T 15:31:00Z+1", "bar", 23.9],
            ["2019-03-02T 15:31:00Z+1", "car", 56.2],
            ["2019-03-02T 15:32:00Z+1", "foo", 2.5],
            ["2019-03-02T 15:32:00Z+1", "bar", -5.2],
            ["2019-05-21T 15:33:00Z+1", "car", 1802.0],
            ["2040-12-31T 00:28:00Z+1", "bar", 90.2],
        ]

        aeroqual = Aeroqual.Aeroqual(self.cfg, self.fields)
        res, _ = aeroqual.validate_data(data, fmt)
        self.assertCountEqual(res, exp)

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
        fmt = "%Y-%m-%d %H:%M:%S"
        exp = [
            ["timestamp", "measurand", "value"],
            ["2019-03-02 15:30:00", "car", 1e5],
        ]

        aeroqual = Aeroqual.Aeroqual(self.cfg, self.fields)
        res, _ = aeroqual.validate_data(data, fmt)
        self.assertEqual(res, exp)

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
        fmt = "%Y-%m-%d %H:%M:%S"

        aeroqual = Aeroqual.Aeroqual(self.cfg, self.fields)
        with self.assertRaises(utils.ValidateDataError):
            res, _ = aeroqual.validate_data(data, fmt)

    def test_no_data(self):
        data = [
            ["not used", "foo", "timestamp", "bar", "unused", "car"],
        ]
        fmt = "%Y-%m-%d %H:%M:%S"

        aeroqual = Aeroqual.Aeroqual(self.cfg, self.fields)
        res, _ = aeroqual.validate_data(data, fmt)
        exp = [["timestamp", "measurand", "value"]]
        self.assertEqual(res, exp)

    def test_empty_list(self):
        data = []
        fmt = "%Y-%m-%d %H:%M:%S"

        aeroqual = Aeroqual.Aeroqual(self.cfg, self.fields)
        with self.assertRaises(utils.ValidateDataError):
            aeroqual.validate_data(data, fmt)

    def test_None(self):
        data = None
        fmt = "%Y-%m-%d %H:%M:%S"
        aeroqual = Aeroqual.Aeroqual(self.cfg, self.fields)
        with self.assertRaises(utils.ValidateDataError):
            aeroqual.validate_data(data, fmt)

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
        fmt = "%Y-%m-%d %H:%M:%S"
        aeroqual = Aeroqual.Aeroqual(self.cfg, self.fields)
        with self.assertRaises(utils.ValidateDataError):
            aeroqual.validate_data(data, fmt)

    def test_missing_measurands(self):
        # Here are asking for measurands that aren't in the raw data. Should
        # pass as very well could have situation where different devices
        # from same manufacturer have different sensor equipped
        fields_copy = self.fields.copy()
        fields_copy.append({"id": "donkey", "webid": "donkey", "scale": 1})
        aeroqual = Aeroqual.Aeroqual(self.cfg, fields_copy)
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
        fmt = "%Y-%m-%d %H:%M:%S"
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

        res, _ = aeroqual.validate_data(data, fmt)
        self.assertCountEqual(res, exp)

    def test_invalid_timestamp_format(self):
        # If forget to add the %%s, then timestamps won't be parsed and thus
        # will get empty output
        cfg_copy = self.cfg.copy()
        cfg_copy["timestamp_format"] = "Y-m-d H:M"
        aeroqual = Aeroqual.Aeroqual(cfg_copy, self.fields)
        fmt = "%Y-%m-%d %H:%M:%S"

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
        res, _ = aeroqual.validate_data(data, fmt)
        exp = [["timestamp", "measurand", "value"]]
        self.assertEqual(res, exp)

    def test_invalid_timestamp_format2(self):
        # If ask for wrong format, i.e. %y (00, 01) rather than %Y (2000, 2001),
        # then should also find no valid timestamps
        cfg_copy = self.cfg.copy()
        cfg_copy["timestamp_format"] = "%%y-%%m-%%d %%H:%%M"
        aeroqual = Aeroqual.Aeroqual(cfg_copy, self.fields)
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
        fmt = "%Y-%m-%d %H:%M:%S"
        res, _ = aeroqual.validate_data(data, fmt)
        exp = [["timestamp", "measurand", "value"]]
        self.assertEqual(res, exp)


if __name__ == "__main__":
    unittest.main()
