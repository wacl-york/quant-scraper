"""
    test_parse_to_csv.py
    ~~~~~~~~~~~~~~~~~~~~

    Unit tests for cli.parse_to_csv() methods.
"""


import unittest
from unittest.mock import MagicMock
from collections import defaultdict
import configparser
import quantscraper.manufacturers.Aeroqual as Aeroqual
import quantscraper.manufacturers.AQMesh as AQMesh
import quantscraper.manufacturers.Zephyr as Zephyr
import quantscraper.manufacturers.MyQuantAQ as MyQuantAQ
from quantscraper.utils import DataParseError

# NB: The calling function, Manufacturer.process() shouldn't allow any None
# values to be passed into parse_csv(), so am currently not testing for it,
# but would be wise to add such functionality


class TestAeroqual(unittest.TestCase):
    # Aeroqual's raw data is organised as a CSV in a raw string, i.e.
    # \r\n delimiting lines and , delimiting columns
    # However, it has 6 empty header lines containing metadata

    start_dt = MagicMock()
    end_dt = MagicMock()
    cfg = defaultdict(str)
    cfg["lines_skip"] = 6
    fields = []
    aeroqual = Aeroqual.Aeroqual(start_dt, end_dt, cfg, fields)

    def test_success(self):
        raw_data = "header1\r\nheader2\r\nheader3\r\nheader4\r\nheader5\r\nheader6\r\nNO2,CO2,O3\r\n1,2,3\r\n4,5,6\r\n7,8,9"
        exp = [["NO2", "CO2", "O3"], ["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"]]
        res = self.aeroqual.parse_to_csv(raw_data)
        self.assertEqual(res, exp)

    def test_lines_skip_low(self):
        # Ensure that lines_skip is appropiately used. Here it is reduced,
        # meaning will throw error as have mismatched column sizes
        cfg_copy = self.cfg.copy()
        cfg_copy["lines_skip"] = 4
        aeroqual2 = Aeroqual.Aeroqual(self.start_dt, self.end_dt, cfg_copy, self.fields)

        raw_data = "header1\r\nheader2\r\nheader3\r\nheader4\r\nheader5\r\nheader6\r\nNO2,CO2,O3\r\n1,2,3\r\n4,5,6\r\n7,8,9"
        exp = [
            ["header5"],
            ["header6"],
            ["NO2", "CO2", "O3"],
            ["1", "2", "3"],
            ["4", "5", "6"],
            ["7", "8", "9"],
        ]
        with self.assertRaises(DataParseError):
            aeroqual2.parse_to_csv(raw_data)

    def test_lines_skip_high(self):
        # Ensure that lines_skip is appropiately used. Here it is increased,
        # meaning will lose actual data rows
        cfg_copy = self.cfg.copy()
        cfg_copy["lines_skip"] = 8
        aeroqual2 = Aeroqual.Aeroqual(self.start_dt, self.end_dt, cfg_copy, self.fields)

        raw_data = "header1\r\nheader2\r\nheader3\r\nheader4\r\nheader5\r\nheader6\r\nNO2,CO2,O3\r\n1,2,3\r\n4,5,6\r\n7,8,9"
        exp = [["4", "5", "6"], ["7", "8", "9"]]
        res = aeroqual2.parse_to_csv(raw_data)
        self.assertEqual(res, exp)

    def test_empty_string(self):
        # If have empty value (2 consecutive commas) then should get empty
        # string in output CSV data.
        # Have removed 2, 4, and 9
        raw_data = "header1\r\nheader2\r\nheader3\r\nheader4\r\nheader5\r\nheader6\r\nNO2,CO2,O3\r\n1,,3\r\n,5,6\r\n7,8,"
        exp = [["NO2", "CO2", "O3"], ["1", "", "3"], ["", "5", "6"], ["7", "8", ""]]
        res = self.aeroqual.parse_to_csv(raw_data)
        self.assertEqual(res, exp)

    def test_fewer_lines_headers(self):
        # What happens if have fewer lines available than headers to skip?
        raw_data = "header1\r\nheader2\r\nheader3\r\nheader4"
        with self.assertRaises(DataParseError):
            self.aeroqual.parse_to_csv(raw_data)

    def test_no_data(self):
        # What happens if have sufficient headers, but no data?
        raw_data = "header1\r\nheader2\r\nheader3\r\nheader4\r\nheader5\r\nheader6"
        with self.assertRaises(DataParseError):
            self.aeroqual.parse_to_csv(raw_data)

    def test_missing_data(self):
        # Expect error to be thrown if have unbalanced columns
        # Have set third row to only have 2 values (7 & 8)
        # This is an error as have no way of knowing if this missing value is
        # from NO2, CO2, or O3
        raw_data = "header1\r\nheader2\r\nheader3\r\nheader4\r\nheader5\r\nheader6\r\nNO2 CO2 O3\r\n1,2,3\r\n4,5,6\r\n7,8"
        with self.assertRaises(DataParseError):
            self.aeroqual.parse_to_csv(raw_data)

    def test_one_column(self):
        # Will want code to throw error if have just 1 column of data, as
        # could indicate the delimiter is wrong. It is also unlikely we'd ever
        # be in a situation with a single column of data being returned.
        # Better to warn user of this behaviour than to silently pass
        raw_data = "header1\r\nheader2\r\nheader3\r\nheader4\r\nheader5\r\nheader6\r\nNO2 CO2 O3\r\n1 2 3\r\n4 5 6\r\n7 8 9"
        with self.assertRaises(DataParseError):
            self.aeroqual.parse_to_csv(raw_data)


class TestAQMesh(unittest.TestCase):
    # The JSON returned by the API call has 2 entries:
    #   - Headers
    #   - Rows
    # Rows are just clean data in the required CSV format
    # Headers is a list of dicts, where each entry in the list is a column, and
    #   each entry in the dict contains metadata. We want the 'Header' field which
    #   holds the field name.
    start_dt = MagicMock()
    end_dt = MagicMock()
    cfg = defaultdict(str)
    fields = []
    aqmesh = AQMesh.AQMesh(start_dt, end_dt, cfg, fields)

    def test_success(self):
        raw_headers = [
            {"Header": "NO2", "Unit": "ug/m3"},
            {"Header": "CO2", "Unit": "ug/m3"},
            {"Header": "O3", "Unit": "ug/m3"},
        ]
        raw_data = [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"]]
        raw_combined = dict(Headers=raw_headers, Rows=raw_data)

        exp = [["NO2", "CO2", "O3"], ["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"]]
        res = self.aqmesh.parse_to_csv(raw_combined)
        self.assertEqual(res, exp)

    def test_empty_string(self):
        # If have empty strings but commas still present then should be
        # parsable.
        # Have removed 2, 4, and 9
        raw_headers = [
            {"Header": "NO2", "Unit": "ug/m3"},
            {"Header": "CO2", "Unit": "ug/m3"},
            {"Header": "O3", "Unit": "ug/m3"},
        ]
        raw_data = [["1", "", "3"], ["", "5", "6"], ["7", "8", ""]]
        raw_combined = dict(Headers=raw_headers, Rows=raw_data)

        exp = [["NO2", "CO2", "O3"], ["1", "", "3"], ["", "5", "6"], ["7", "8", ""]]
        res = self.aqmesh.parse_to_csv(raw_combined)
        self.assertEqual(res, exp)

    def test_unbalanced_headers_and_rows(self):
        # What happens if there are a different number of headers to rows
        # Have 2 headers but 3 columns
        raw_headers = [
            {"Header": "NO2", "Unit": "ug/m3"},
            {"Header": "O3", "Unit": "ug/m3"},
        ]
        raw_data = [["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"]]
        raw_combined = dict(Headers=raw_headers, Rows=raw_data)

        with self.assertRaises(DataParseError):
            self.aqmesh.parse_to_csv(raw_combined)

    def test_missing_data(self):
        # What happens if there are a different number of columns?
        # Second row only has 2 columns
        # This should throw an error as have no way of knowing which value is
        # missing. Is it NO2, or CO2 or O3? Cannot tell so need to alert user
        raw_headers = [
            {"Header": "NO2", "Unit": "ug/m3"},
            {"Header": "CO2", "Unit": "ug/m3"},
            {"Header": "O3", "Unit": "ug/m3"},
        ]
        raw_data = [["1", "2", "3"], ["4", "6"], ["7", "8", "9"]]
        raw_combined = dict(Headers=raw_headers, Rows=raw_data)

        with self.assertRaises(DataParseError):
            self.aqmesh.parse_to_csv(raw_combined)


class TestZephyr(unittest.TestCase):
    # The JSON returned by Zephyr's API call has 4 attributes, but we're only
    # interested in 'data'.
    # This attribute has a further 5 fields, one for each averaging period.
    # Once have selected averaging window, have another dict:
    # {measurand: {
    #              header: [],
    #              data: [],
    #              data_hash: str
    #             }
    # The 'header' entries contain metadata, the main one that will be useful
    # here is the CSVOrder int.
    # 'data' is the list of values, and 'data_hash' is just a hash

    start_dt = MagicMock()
    end_dt = MagicMock()
    cfg = defaultdict(str)
    cfg["averaging_window"] = "Unaveraged"
    cfg["slot"] = "slotB"
    fields = []
    zephyr = Zephyr.Zephyr(start_dt, end_dt, cfg, fields)

    def test_success(self):
        # Put measurands in out of order to ensure the CSVOrder flag is used
        raw = {
            "foo": "bar",
            "data": {
                "5mins": "foo",
                "Unaveraged": {
                    "slotB": {
                        "CO2": {
                            "header": {"CSVOrder": 1, "foo": "bar"},
                            "data": ["2", "5", "8"],
                        },
                        "O3": {
                            "header": {"CSVOrder": 2, "foo": "bar"},
                            "data": ["3", "6", "9"],
                        },
                        "NO2": {
                            "header": {"CSVOrder": 0, "foo": "bar"},
                            "data": ["1", "4", "7"],
                        },
                    }
                },
            },
        }

        exp = [["NO2", "CO2", "O3"], ["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"]]
        res = self.zephyr.parse_to_csv(raw)
        self.assertEqual(res, exp)

    def test_can_use_alternative_slot(self):
        # Put data in non-selected slot A, code should be able to recognise this
        raw = {
            "foo": "bar",
            "data": {
                "5mins": "foo",
                "Unaveraged": {
                    "slotA": {
                        "CO2": {
                            "header": {"CSVOrder": 1, "foo": "bar"},
                            "data": ["2", "5", "8"],
                        },
                        "O3": {
                            "header": {"CSVOrder": 2, "foo": "bar"},
                            "data": ["3", "6", "9"],
                        },
                        "NO2": {
                            "header": {"CSVOrder": 0, "foo": "bar"},
                            "data": ["1", "4", "7"],
                        },
                    }
                },
            },
        }

        exp = [["NO2", "CO2", "O3"], ["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"]]
        res = self.zephyr.parse_to_csv(raw)
        self.assertEqual(res, exp)

    def test_empty_strings(self):
        # Test with empty strings
        # Have removed 2, 4, 9
        # Put data in non-selected slot A, code should be able to recognise this
        raw = {
            "foo": "bar",
            "data": {
                "5mins": "foo",
                "Unaveraged": {
                    "slotA": {
                        "CO2": {
                            "header": {"CSVOrder": 1, "foo": "bar"},
                            "data": ["", "5", "8"],
                        },
                        "O3": {
                            "header": {"CSVOrder": 2, "foo": "bar"},
                            "data": ["3", "6", ""],
                        },
                        "NO2": {
                            "header": {"CSVOrder": 0, "foo": "bar"},
                            "data": ["1", "", "7"],
                        },
                    }
                },
            },
        }

        exp = [["NO2", "CO2", "O3"], ["1", "", "3"], ["", "5", "6"], ["7", "8", ""]]
        res = self.zephyr.parse_to_csv(raw)
        self.assertEqual(res, exp)

    def test_missing_data(self):
        # O3 has 1 fewer observation
        # This is an error as we aren't sure which timepoint is missing, and so
        # cannot even add a 'missing data' flag for this observation.
        raw = {
            "foo": "bar",
            "data": {
                "5mins": "foo",
                "Unaveraged": {
                    "slotB": {
                        "CO2": {
                            "header": {"CSVOrder": 1, "foo": "bar"},
                            "data": ["2", "5", "8"],
                        },
                        "O3": {
                            "header": {"CSVOrder": 2, "foo": "bar"},
                            "data": ["6", "9"],
                        },
                        "NO2": {
                            "header": {"CSVOrder": 0, "foo": "bar"},
                            "data": ["1", "4", "7"],
                        },
                    }
                },
            },
        }

        with self.assertRaises(DataParseError):
            self.zephyr.parse_to_csv(raw)


class TestQuantAQ(unittest.TestCase):
    # The JSON returned by quantaq's API call is in the format of a list of
    # dicts, where each entry in the list is a row.
    # The function I've produced has had to, by necessity, hardcode lat and lon
    start_dt = MagicMock()
    end_dt = MagicMock()
    cfg = defaultdict(str)
    fields = []
    myquantaq = MyQuantAQ.MyQuantAQ(start_dt, end_dt, cfg, fields)

    def test_success(self):
        # Currently not a very robust function, as it will error
        # if it doesn't have the 'geo' dict available
        raw_data = {
            "raw": "foo",
            "final": [
                {
                    "NO2": "1",
                    "CO2": "2",
                    "O3": "3",
                    "geo": {"lat": "3.5", "lon": "4.5"},
                },
                {
                    "NO2": "4",
                    "CO2": "5",
                    "O3": "6",
                    "geo": {"lat": "5.5", "lon": "6.5"},
                },
                {
                    "NO2": "7",
                    "CO2": "8",
                    "O3": "9",
                    "geo": {"lat": "7.5", "lon": "8.5"},
                },
            ],
        }

        exp = [
            ["NO2", "CO2", "O3", "lat", "lon"],
            ["1", "2", "3", "3.5", "4.5"],
            ["4", "5", "6", "5.5", "6.5"],
            ["7", "8", "9", "7.5", "8.5"],
        ]
        res = self.myquantaq.parse_to_csv(raw_data)
        self.assertEqual(res, exp)

    def test_missing_data(self):
        # Have removed CO2's second observation and O3's third
        # Now, unlike the other 3 manufacturers, we can handle this missingness
        # as each observation is directly tied to a timepoint.
        # So if a measurand isn't available for a particular timepoint, then we
        # can encode this.
        # Missing values are encoded as NaN, as per Seba's request
        raw_data = {
            "raw": "foo",
            "final": [
                {
                    "NO2": "1",
                    "CO2": "2",
                    "O3": "3",
                    "geo": {"lat": "3.5", "lon": "4.5"},
                },
                {"NO2": "4", "O3": "6", "geo": {"lat": "5.5", "lon": "6.5"}},
                {"NO2": "7", "CO2": "8", "geo": {"lat": "7.5", "lon": "8.5"},},
            ],
        }

        exp = [
            ["NO2", "CO2", "O3", "lat", "lon"],
            ["1", "2", "3", "3.5", "4.5"],
            ["4", "NaN", "6", "5.5", "6.5"],
            ["7", "8", "NaN", "7.5", "8.5"],
        ]
        res = self.myquantaq.parse_to_csv(raw_data)
        self.assertEqual(res, exp)

    def test_empty_string(self):
        # Can check parsing works when data contains empty strings
        # Note that an empty string in the raw data will result in an empty
        # string in the parsed CSV data
        # *BUT* a missing value in the raw data will result in a 'NaN' string
        # in the parsed CSV data.
        # This allows the validation script to differentiate between these 2
        # types of errors, although it currently doesn't.

        raw_data = {
            "raw": "foo",
            "final": [
                {"NO2": "1", "CO2": "", "O3": "3", "geo": {"lat": "", "lon": "4.5"},},
                {"NO2": "4", "O3": "6", "geo": {"lat": "5.5", "lon": "6.5"}},
                {"NO2": "7", "CO2": "", "geo": {"lat": "7.5", "lon": ""},},
            ],
        }

        exp = [
            ["NO2", "CO2", "O3", "lat", "lon"],
            ["1", "", "3", "", "4.5"],
            ["4", "NaN", "6", "5.5", "6.5"],
            ["7", "", "NaN", "7.5", ""],
        ]
        res = self.myquantaq.parse_to_csv(raw_data)
        self.assertEqual(res, exp)


if __name__ == "__main__":
    unittest.main()
