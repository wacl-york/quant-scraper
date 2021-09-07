"""
    test_parse_to_csv.py
    ~~~~~~~~~~~~~~~~~~~~

    Unit tests for cli.parse_to_csv() methods.
"""


import unittest
from collections import defaultdict
import quantscraper.manufacturers.Aeroqual as Aeroqual
import quantscraper.manufacturers.AQMesh as AQMesh
import quantscraper.manufacturers.Zephyr as Zephyr
import quantscraper.manufacturers.MyQuantAQ as MyQuantAQ
import quantscraper.manufacturers.AURN as AURN
import quantscraper.manufacturers.PurpleAir as PurpleAir
from quantscraper.utils import DataParseError
import numpy as np

# NB: The calling function, Manufacturer.process() shouldn't allow any None
# values to be passed into parse_csv(), so am currently not testing for it,
# but would be wise to add such functionality


class TestAeroqual(unittest.TestCase):
    # Aeroqual's raw data is organised as a JSON with [{Time: val, O3: val}, ]
    cfg = defaultdict(str)
    fields = []
    aeroqual = Aeroqual.Aeroqual(cfg, fields)

    def test_success(self):
        raw_data = [
            {"time": "2020-03-04", "NO2": 1, "O3": 3},
            {"time": "2020-03-05", "NO2": 2, "O3": 4},
            {"time": "2020-03-06", "NO2": 5, "O3": 6},
        ]

        exp = [
            ["time", "NO2", "O3"],
            ["2020-03-04", 1, 3],
            ["2020-03-05", 2, 4],
            ["2020-03-06", 5, 6],
        ]
        res = self.aeroqual.parse_to_csv(raw_data)
        self.assertEqual(res, exp)

    def test_nonalphabetical(self):
        # Check that it doesn't matter if data isn't ordered alphabetically
        raw_data = [
            {"time": "2020-03-04", "O3": 1, "NO2": 3},
            {"time": "2020-03-05", "O3": 2, "NO2": 4},
            {"time": "2020-03-06", "O3": 5, "NO2": 6},
        ]

        exp = [
            ["time", "O3", "NO2"],
            ["2020-03-04", 1, 3],
            ["2020-03-05", 2, 4],
            ["2020-03-06", 5, 6],
        ]
        res = self.aeroqual.parse_to_csv(raw_data)
        self.assertEqual(res, exp)

    def test_order_changes(self):
        # Check that order of attributes doesn't matter, as
        # Pandas orders by first row
        raw_data = [
            {"time": "2020-03-04", "O3": 1, "NO2": 3},
            {"NO2": 4, "O3": 2, "time": "2020-03-05"},
            {"O3": 5, "time": "2020-03-06", "NO2": 6},
        ]

        exp = [
            ["time", "O3", "NO2"],
            ["2020-03-04", 1, 3],
            ["2020-03-05", 2, 4],
            ["2020-03-06", 5, 6],
        ]
        res = self.aeroqual.parse_to_csv(raw_data)
        self.assertEqual(res, exp)

    def test_missing_measurands(self):
        # Check that returns an empty value for a missing value
        raw_data = [
            {"time": "2020-03-04", "O3": 1.0, "NO2": 3.2},
            {"NO2": 4.3, "O3": 2.1, "time": "2020-03-05"},
            {"time": "2020-03-06", "NO2": 6.9},
        ]

        exp = [
            ["time", "O3", "NO2"],
            ["2020-03-04", 1.0, 3.2],
            ["2020-03-05", 2.1, 4.3],
            ["2020-03-06", float("nan"), 6.9],
        ]

        res = self.aeroqual.parse_to_csv(raw_data)

        # Need to cast all to string here, as otherwise can't compare NaN
        # I.e. in python NaN == NaN returns False
        exp_str = [[str(x) for x in row] for row in exp]
        res_str = [[str(x) for x in row] for row in res]

        self.assertEqual(res_str, exp_str)

    def test_empty_measurand(self):
        # Check that returns an empty value for a missing value where the key is
        # present but the value is an empty string
        raw_data = [
            {"time": "2020-03-04", "O3": 1.0, "NO2": 3.2},
            {"NO2": 4.3, "O3": 2.1, "time": "2020-03-05"},
            {"O3": "", "time": "2020-03-06", "NO2": 6.9},
        ]

        exp = [
            ["time", "O3", "NO2"],
            ["2020-03-04", 1.0, 3.2],
            ["2020-03-05", 2.1, 4.3],
            ["2020-03-06", "", 6.9],
        ]

        res = self.aeroqual.parse_to_csv(raw_data)
        self.assertEqual(res, exp)

    def test_no_data(self):
        # Check that empty list returns empty list
        raw_data = []

        exp = [[]]

        res = self.aeroqual.parse_to_csv(raw_data)
        self.assertEqual(res, exp)


class TestAQMesh(unittest.TestCase):
    # The JSON returned by the API call has 2 entries:
    #   - Headers
    #   - Rows
    # Rows are just clean data in the required CSV format
    # Headers is a list of dicts, where each entry in the list is a column, and
    #   each entry in the dict contains metadata. We want the 'Header' field which
    #   holds the field name.
    cfg = defaultdict(str)
    fields = []
    aqmesh = AQMesh.AQMesh(cfg, fields)

    def test_success(self):
        raw_data = {
            "1": {
                "Timestamp": {
                    "Timestamp": "2020-03-04 12:32",
                    "Convention": "Beginning",
                },
                "Channels": [
                    {"SensorLabel": "CO2", "Scaled": {"Reading": 2}},
                    {"SensorLabel": "NO2", "Scaled": {"Reading": 1}},
                    {"SensorLabel": "O3", "Scaled": {"Reading": 3}},
                ],
            },
            "2": {
                "Timestamp": {
                    "Timestamp": "2020-03-04 12:33",
                    "Convention": "Beginning",
                },
                "Channels": [
                    {"SensorLabel": "CO2", "Scaled": {"Reading": 5}},
                    {"SensorLabel": "NO2", "Scaled": {"Reading": 4}},
                    {"SensorLabel": "O3", "Scaled": {"Reading": 6}},
                ],
            },
            "3": {
                "Timestamp": {
                    "Timestamp": "2020-03-04 12:34",
                    "Convention": "Beginning",
                },
                "Channels": [
                    {"SensorLabel": "CO2", "Scaled": {"Reading": 8}},
                    {"SensorLabel": "NO2", "Scaled": {"Reading": 7}},
                    {"SensorLabel": "O3", "Scaled": {"Reading": 9}},
                ],
            },
        }

        exp = [
            ["Timestamp", "CO2", "NO2", "O3"],
            ["2020-03-04 12:32", 2, 1, 3],
            ["2020-03-04 12:33", 5, 4, 6],
            ["2020-03-04 12:34", 8, 7, 9],
        ]

        res = self.aqmesh.parse_to_csv(raw_data)
        self.assertEqual(res, exp)

    def test_missing_timestamp(self):
        # The first timestamp object isn't present.
        # Should still retrieve data from the others entries.
        raw_data = {
            "1": {
                "Channels": [
                    {"SensorLabel": "CO2", "Scaled": {"Reading": 2}},
                    {"SensorLabel": "NO2", "Scaled": {"Reading": 1}},
                    {"SensorLabel": "O3", "Scaled": {"Reading": 3}},
                ]
            },
            "2": {
                "Timestamp": {
                    "Timestamp": "2020-03-04 12:33",
                    "Convention": "Beginning",
                },
                "Channels": [
                    {"SensorLabel": "CO2", "Scaled": {"Reading": 5}},
                    {"SensorLabel": "NO2", "Scaled": {"Reading": 4}},
                    {"SensorLabel": "O3", "Scaled": {"Reading": 6}},
                ],
            },
            "3": {
                "Timestamp": {
                    "Timestamp": "2020-03-04 12:34",
                    "Convention": "Beginning",
                },
                "Channels": [
                    {"SensorLabel": "CO2", "Scaled": {"Reading": 8}},
                    {"SensorLabel": "NO2", "Scaled": {"Reading": 7}},
                    {"SensorLabel": "O3", "Scaled": {"Reading": 9}},
                ],
            },
        }

        exp = [
            ["Timestamp", "CO2", "NO2", "O3"],
            ["2020-03-04 12:33", 5, 4, 6],
            ["2020-03-04 12:34", 8, 7, 9],
        ]
        res = self.aqmesh.parse_to_csv(raw_data)
        self.assertEqual(res, exp)

    def test_missing_channels(self):
        # If don't have Channels attribute then shouldn't get data from that
        # timepoint. Have removed Channels from first object.
        raw_data = {
            "1": {
                "Timestamp": {
                    "Timestamp": "2020-03-04 12:32",
                    "Convention": "Beginning",
                }
            },
            "2": {
                "Timestamp": {
                    "Timestamp": "2020-03-04 12:33",
                    "Convention": "Beginning",
                },
                "Channels": [
                    {"SensorLabel": "CO2", "Scaled": {"Reading": 5}},
                    {"SensorLabel": "NO2", "Scaled": {"Reading": 4}},
                    {"SensorLabel": "O3", "Scaled": {"Reading": 6}},
                ],
            },
            "3": {
                "Timestamp": {
                    "Timestamp": "2020-03-04 12:34",
                    "Convention": "Beginning",
                },
                "Channels": [
                    {"SensorLabel": "CO2", "Scaled": {"Reading": 8}},
                    {"SensorLabel": "NO2", "Scaled": {"Reading": 7}},
                    {"SensorLabel": "O3", "Scaled": {"Reading": 9}},
                ],
            },
        }

        exp = [
            ["Timestamp", "CO2", "NO2", "O3"],
            ["2020-03-04 12:33", 5, 4, 6],
            ["2020-03-04 12:34", 8, 7, 9],
        ]

        res = self.aqmesh.parse_to_csv(raw_data)
        self.assertEqual(res, exp)

    def test_empty_channels(self):
        # If have Channels object but it's empty then should also not return
        # data from that timepoint. Have removed first time-point's Channels
        # entries.
        raw_data = {
            "1": {
                "Timestamp": {
                    "Timestamp": "2020-03-04 12:32",
                    "Convention": "Beginning",
                },
            },
            "2": {
                "Timestamp": {
                    "Timestamp": "2020-03-04 12:33",
                    "Convention": "Beginning",
                },
                "Channels": [
                    {"SensorLabel": "CO2", "Scaled": {"Reading": 5}},
                    {"SensorLabel": "NO2", "Scaled": {"Reading": 4}},
                    {"SensorLabel": "O3", "Scaled": {"Reading": 6}},
                ],
            },
            "3": {
                "Timestamp": {
                    "Timestamp": "2020-03-04 12:34",
                    "Convention": "Beginning",
                },
                "Channels": [
                    {"SensorLabel": "CO2", "Scaled": {"Reading": 8}},
                    {"SensorLabel": "NO2", "Scaled": {"Reading": 7}},
                    {"SensorLabel": "O3", "Scaled": {"Reading": 9}},
                ],
            },
        }

        exp = [
            ["Timestamp", "CO2", "NO2", "O3"],
            ["2020-03-04 12:33", 5, 4, 6],
            ["2020-03-04 12:34", 8, 7, 9],
        ]

        res = self.aqmesh.parse_to_csv(raw_data)
        self.assertEqual(res, exp)

    def test_missing_sensor_label(self):
        # If missing a sensor label attribute, then should simply not have data
        # for that observation. Have removed NO2's second sensor label
        raw_data = {
            "1": {
                "Timestamp": {
                    "Timestamp": "2020-03-04 12:32",
                    "Convention": "Beginning",
                },
                "Channels": [
                    {"SensorLabel": "CO2", "Scaled": {"Reading": 2}},
                    {"SensorLabel": "NO2", "Scaled": {"Reading": 1}},
                    {"SensorLabel": "O3", "Scaled": {"Reading": 3}},
                ],
            },
            "2": {
                "Timestamp": {
                    "Timestamp": "2020-03-04 12:33",
                    "Convention": "Beginning",
                },
                "Channels": [
                    {"SensorLabel": "CO2", "Scaled": {"Reading": 5}},
                    {"Scaled": {"Reading": 4}},
                    {"SensorLabel": "O3", "Scaled": {"Reading": 6}},
                ],
            },
            "3": {
                "Timestamp": {
                    "Timestamp": "2020-03-04 12:34",
                    "Convention": "Beginning",
                },
                "Channels": [
                    {"SensorLabel": "CO2", "Scaled": {"Reading": 8}},
                    {"SensorLabel": "NO2", "Scaled": {"Reading": 7}},
                    {"SensorLabel": "O3", "Scaled": {"Reading": 9}},
                ],
            },
        }

        exp = [
            ["Timestamp", "CO2", "NO2", "O3"],
            ["2020-03-04 12:32", 2, 1, 3],
            ["2020-03-04 12:33", 5, "", 6],
            ["2020-03-04 12:34", 8, 7, 9],
        ]

        res = self.aqmesh.parse_to_csv(raw_data)
        self.assertEqual(res, exp)

    def test_missing_scaled(self):
        # Likewise, if missing the Scaled attribute then should simply have
        # empty value for this observation.
        # Have removed it from CO2's third observation
        raw_data = {
            "1": {
                "Timestamp": {
                    "Timestamp": "2020-03-04 12:32",
                    "Convention": "Beginning",
                },
                "Channels": [
                    {"SensorLabel": "CO2", "Scaled": {"Reading": 2}},
                    {"SensorLabel": "NO2", "Scaled": {"Reading": 1}},
                    {"SensorLabel": "O3", "Scaled": {"Reading": 3}},
                ],
            },
            "2": {
                "Timestamp": {
                    "Timestamp": "2020-03-04 12:33",
                    "Convention": "Beginning",
                },
                "Channels": [
                    {"SensorLabel": "CO2", "Scaled": {"Reading": 5}},
                    {"SensorLabel": "NO2", "Scaled": {"Reading": 4}},
                    {"SensorLabel": "O3", "Scaled": {"Reading": 6}},
                ],
            },
            "3": {
                "Timestamp": {
                    "Timestamp": "2020-03-04 12:34",
                    "Convention": "Beginning",
                },
                "Channels": [
                    {"SensorLabel": "CO2",},
                    {"SensorLabel": "NO2", "Scaled": {"Reading": 7}},
                    {"SensorLabel": "O3", "Scaled": {"Reading": 9}},
                ],
            },
        }

        exp = [
            ["Timestamp", "CO2", "NO2", "O3"],
            ["2020-03-04 12:32", 2, 1, 3],
            ["2020-03-04 12:33", 5, 4, 6],
            ["2020-03-04 12:34", "", 7, 9],
        ]

        res = self.aqmesh.parse_to_csv(raw_data)
        self.assertEqual(res, exp)


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

    cfg = defaultdict(str)
    cfg["averaging_window"] = "Unaveraged"
    cfg["slot"] = "slotB"
    fields = []
    zephyr = Zephyr.Zephyr(cfg, fields)

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
    cfg = defaultdict(str)
    fields = []
    myquantaq = MyQuantAQ.MyQuantAQ(cfg, fields)

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
            ["4", np.nan, "6", "5.5", "6.5"],
            ["7", "8", np.nan, "7.5", "8.5"],
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
            ["4", np.nan, "6", "5.5", "6.5"],
            ["7", "", np.nan, "7.5", ""],
        ]
        res = self.myquantaq.parse_to_csv(raw_data)
        self.assertEqual(res, exp)


class TestAURN(unittest.TestCase):
    # The JSON returned by the API call has 1 entry per pollutant.
    # Each of these objects has a single object, "values", which is a list of
    # dicts representing recordings, where each dict has a "timestamp" (POSIX ms)
    # and a "value" (float).
    # The pollutants have numerical IDs
    cfg = defaultdict(str)
    fields = []
    aurn = AURN.AURN(cfg, fields)

    def test_success(self):
        self.aurn.timestamp_format = "%Y-%m-%d %H:%M:%S"
        raw = {
            "2380": {
                "values": [
                    {"timestamp": 1584406800000, "value": 23.2},
                    {"timestamp": 1584806800000, "value": 43.3},
                ]
            },
            "2383": {
                "values": [
                    {"timestamp": 1584406800000, "value": -21.2},
                    {"timestamp": 1584806800000, "value": 0.0},
                ]
            },
        }

        exp = [
            ["timestamp", "2380", "2383"],
            ["2020-03-17 01:00:00", 23.2, -21.2],
            ["2020-03-21 16:06:40", 43.3, 0.0],
        ]
        res = self.aurn.parse_to_csv(raw)
        self.assertEqual(res, exp)

    def test_empty_dict(self):
        # A completely empty dict should return empty rows
        self.aurn.timestamp_format = "%Y-%m-%d %H:%M:%S"
        raw = {}

        exp = []
        res = self.aurn.parse_to_csv(raw)
        self.assertEqual(res, exp)

    def test_no_values_attributes(self):
        # If have time series objects but not values attribute
        # then shouldn't return any data for this object
        self.aurn.timestamp_format = "%Y-%m-%d %H:%M:%S"
        raw = {"2380": {"foo": "bar"}, "2383": {"bar": "foo"}}

        exp = []
        res = self.aurn.parse_to_csv(raw)
        self.assertEqual(res, exp)

    def test_1_missing_values(self):
        # If have values attribute for one time series but not the other
        # should just get 1 column in output
        self.aurn.timestamp_format = "%Y-%m-%d %H:%M:%S"
        raw = {
            "2380": {"foo": "bar"},
            "2383": {
                "values": [
                    {"timestamp": 1584406800000, "value": -21.2},
                    {"timestamp": 1584806800000, "value": 0.0},
                ]
            },
        }

        exp = [
            ["timestamp", "2383"],
            ["2020-03-17 01:00:00", -21.2],
            ["2020-03-21 16:06:40", 0.0],
        ]
        res = self.aurn.parse_to_csv(raw)
        self.assertEqual(res, exp)

    def test_empty_values_attributes(self):
        # If have empty values then should return empty list
        self.aurn.timestamp_format = "%Y-%m-%d %H:%M:%S"
        raw = {"2380": {"values": []}, "2383": {"values": []}}

        exp = []
        res = self.aurn.parse_to_csv(raw)
        self.assertEqual(res, exp)

    def test_1_empty_values(self):
        # If empty values attribute for one time series but not the other
        # should just get 1 column in output
        self.aurn.timestamp_format = "%Y-%m-%d %H:%M:%S"
        raw = {
            "2380": {"values": []},
            "2383": {
                "values": [
                    {"timestamp": 1584406800000, "value": -21.2},
                    {"timestamp": 1584806800000, "value": 0.0},
                ]
            },
        }

        exp = [
            ["timestamp", "2383"],
            ["2020-03-17 01:00:00", -21.2],
            ["2020-03-21 16:06:40", 0.0],
        ]
        res = self.aurn.parse_to_csv(raw)
        self.assertEqual(res, exp)

    def test_no_timestamp_or_value(self):
        # If missing a timestamp attribute from a data record then
        # this value shouldn't be in the CSV.
        # If we're just missing a value attribute but have timestamp available
        # then should have a missing (i.e. NaN) value in this column
        # In this test, only the second value from 2383 has both required fields
        self.aurn.timestamp_format = "%Y-%m-%d %H:%M:%S"
        raw = {
            "2380": {"values": [{"value": 23.2}, {"timestamp": 1584806800000,}]},
            "2383": {
                "values": [
                    {"foo": "bar"},
                    {"timestamp": 1584806800000, "value": 0.0},
                    {"timestamp": 1584806900000, "value": 0.1},
                ]
            },
        }

        exp = [
            ["timestamp", "2380", "2383"],
            ["2020-03-21 16:06:40", float("nan"), 0.0],
            ["2020-03-21 16:08:20", float("nan"), 0.1],
        ]
        res = self.aurn.parse_to_csv(raw)

        # Need to cast all to string here, as otherwise can't compare NaN
        # I.e. in python NaN == NaN returns False
        exp_str = [[str(x) for x in row] for row in exp]
        res_str = [[str(x) for x in row] for row in res]
        self.assertEqual(res_str, exp_str)

    def test_timestamp_isnt_posix(self):
        # Here the first value from 2380 isn't posix, so should get nan for
        # this timestamp since 2383 has a clean timestamp for this time
        # And the third timestamp for 2383 isn't posix so shouldn't get any row
        # for this value as don't have a corresponding clean timestamp for 2380
        self.aurn.timestamp_format = "%Y-%m-%d %H:%M:%S"
        raw = {
            "2380": {
                "values": [
                    {"timestamp": "foo", "value": 23.2},
                    {"timestamp": 1584806800000, "value": 43.3},
                ]
            },
            "2383": {
                "values": [
                    {"timestamp": 1584406800000, "value": -21.2},
                    {"timestamp": 1584806800000, "value": 0.0},
                    {"timestamp": "foo", "value": 3.0},
                ]
            },
        }

        exp = [
            ["timestamp", "2380", "2383"],
            ["2020-03-17 01:00:00", np.float("nan"), -21.2],
            ["2020-03-21 16:06:40", 43.3, 0.0],
        ]
        res = self.aurn.parse_to_csv(raw)
        # Need to cast all to string here, as otherwise can't compare NaN
        # I.e. in python NaN == NaN returns False
        exp_str = [[str(x) for x in row] for row in exp]
        res_str = [[str(x) for x in row] for row in res]
        self.assertEqual(res_str, exp_str)

    def test_negative_float_timestamps(self):
        # Negatives and floating timestamps should parse correctly,
        # i.e. as days before Epoch and fractions of seconds.
        # It isn't the role of this method to identify 'unreasonable' timestamps
        self.aurn.timestamp_format = "%Y-%m-%d %H:%M:%S"
        raw = {
            "2380": {
                "values": [
                    {"timestamp": 1584406800000, "value": 23.2},
                    {"timestamp": -23200, "value": 43.3},
                ]
            },
            "2383": {
                "values": [
                    {"timestamp": 1584406800000, "value": -21.2},
                    {"timestamp": 3141.59, "value": 0.0},
                ]
            },
        }

        exp = [
            ["timestamp", "2380", "2383"],
            ["1969-12-31 23:59:36", 43.3, float("nan")],
            ["1970-01-01 00:00:03", float("nan"), 0.0],
            ["2020-03-17 01:00:00", 23.2, -21.2],
        ]
        res = self.aurn.parse_to_csv(raw)
        # Need to cast all to string here, as otherwise can't compare NaN
        # I.e. in python NaN == NaN returns False
        exp_str = [[str(x) for x in row] for row in exp]
        res_str = [[str(x) for x in row] for row in res]
        self.assertEqual(res_str, exp_str)


class TestPurpleAir(unittest.TestCase):
    # PurpleAir's data should already arrive in a CSV format encoded as a
    # string with \r\n delimiting rows and commas columns

    cfg = defaultdict(str)
    fields = []
    pa = PurpleAir.PurpleAir(cfg, fields)

    def test_success(self):
        raw_data = "NO2,CO2,O3\r\n1,2,3\r\n4,5,6\r\n7,8,9"
        exp = [["NO2", "CO2", "O3"], ["1", "2", "3"], ["4", "5", "6"], ["7", "8", "9"]]
        res = self.pa.parse_to_csv(raw_data)
        self.assertEqual(res, exp)

    def test_empty_string(self):
        # If have empty value (2 consecutive commas) then should get empty
        # string in output CSV data.
        # Have removed 2, 4, and 9
        raw_data = "NO2,CO2,O3\r\n1,,3\r\n,5,6\r\n7,8,"
        exp = [["NO2", "CO2", "O3"], ["1", "", "3"], ["", "5", "6"], ["7", "8", ""]]
        res = self.pa.parse_to_csv(raw_data)
        self.assertEqual(res, exp)

    def test_only_header(self):
        # If have header but no data then should return just the header
        raw_data = "NO2,CO2,O3"
        exp = [["NO2", "CO2", "O3"]]
        res = self.pa.parse_to_csv(raw_data)
        self.assertEqual(res, exp)

    def test_empty(self):
        # If have no data then should raise error
        raw_data = ""
        with self.assertRaises(DataParseError):
            self.pa.parse_to_csv(raw_data)

    def test_missing_data(self):
        # Any rows with missing data aren't included in the returned cleaned CSV
        raw_data = "NO2,CO2,O3\r\n1,2,3\r\n4,5,6\r\n7,8"
        exp = [["NO2", "CO2", "O3"], ["1", "2", "3"], ["4", "5", "6"]]
        res = self.pa.parse_to_csv(raw_data)
        self.assertEqual(res, exp)


if __name__ == "__main__":
    unittest.main()
