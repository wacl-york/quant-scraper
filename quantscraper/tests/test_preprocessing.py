"""
    test_connect.py
    ~~~~~~~~~~~~~~~

    Unit tests for Manufacturer.connect() methods.
"""

import unittest
import sys
import configparser
import pandas as pd
import numpy as np

from unittest.mock import patch, MagicMock, Mock, call

# As scripts are stored in a 'bin' directory that isn't part of the quantscraper
# module, need to add the directory to PYTHONPATH so can import the script
sys.path.extend(["bin"])
import daily_preprocessing
import quantscraper.utils as utils


# Functions to test:
# - resample
# - save output


class TestLoadData(unittest.TestCase):
    def test_success(self):
        cfg = configparser.ConfigParser()
        cfg.read("example.ini")
        # Set dummy clean folder
        cfg.set("Main", "local_folder_clean_data", "cleanfoo")

        # Setup example data to return from mock read and expected function
        # output
        example_data = pd.DataFrame(
            {
                "timestamp": ["2012-03-02 10:34:00", "2013-04-02 10:34:00"],
                "measurand": ["co2", "no2"],
                "value": [2.3, 6.2],
            }
        )
        exp = example_data.copy()
        exp["device"] = "dev1"
        timestamp_dt = pd.to_datetime(exp["timestamp"])
        exp["timestamp"] = timestamp_dt

        # Mock file I/O
        with patch("daily_preprocessing.pd") as mock_pd:
            mock_read = Mock(return_value=example_data)
            mock_pd.read_csv = mock_read
            mock_todt = Mock(return_value=timestamp_dt)
            mock_pd.to_datetime = mock_todt

            res = daily_preprocessing.get_data(
                cfg, "manu1", "dev1", "2012-03-12 10:23:55", "2012-04-12 10:56:09"
            )
            print(res)
            print(exp)

            # Format of expected filename is given in utils.CLEAN_DATA_FN
            mock_read.assert_called_once_with(
                "cleanfoo/manu1_dev1_2012-03-12 10:23:55_2012-04-12 10:56:09.csv"
            )

            # Need to use pandas built-in function for asserting data frame
            # equality
            pd.testing.assert_frame_equal(res, exp)

    # Test for FileNotFoundError, but cannot mock
    # pd.errors.EmptyDataError
    def test_file_not_found(self):
        cfg = configparser.ConfigParser()
        cfg.read("example.ini")
        # Set dummy clean folder
        cfg.set("Main", "local_folder_clean_data", "cleanfoo")

        # Mock file I/O
        with patch("daily_preprocessing.pd") as mock_pd:
            mock_read = Mock(side_effect=FileNotFoundError(""))
            mock_pd.read_csv = mock_read

            with self.assertRaises(utils.DataReadingError):
                res = daily_preprocessing.get_data(
                    cfg, "manu1", "dev1", "2012-03-12 10:23:55", "2012-04-12 10:56:09"
                )


class TestLongToWide(unittest.TestCase):
    # Test the function that converts long data to wide.

    def test_success(self):
        # Have CO2 and NO2 at first timestamp, but only CO2 at second
        example_data = pd.DataFrame(
            {
                "timestamp": [
                    "2013-03-17 10:34:00",
                    "2013-03-17 10:34:00",
                    "2013-03-17 10:34:30",
                ],
                "device": ["dev1", "dev1", "dev1"],
                "measurand": ["co2", "no2", "co2"],
                "value": [2.3, 6.2, 2.6],
            }
        )

        exp = pd.DataFrame(
            {
                "timestamp": ["2013-03-17 10:34:00", "2013-03-17 10:34:30"],
                "dev1_co2": [2.3, 2.6],
                "dev1_no2": [6.2, np.nan],
            }
        )
        exp = exp.set_index(["timestamp"])
        exp.columns.name = "measurand"
        res = daily_preprocessing.long_to_wide(example_data)

        pd.testing.assert_frame_equal(res, exp)

    def test_adds_missing_measurands(self):
        # Have CO2 and NO2 at first timestamp, but only CO2 at second,
        # but completely missing CO and O3!
        example_data = pd.DataFrame(
            {
                "timestamp": [
                    "2013-03-17 10:34:00",
                    "2013-03-17 10:34:00",
                    "2013-03-17 10:34:30",
                ],
                "device": ["dev1", "dev1", "dev1"],
                "measurand": ["co2", "no2", "co2"],
                "value": [2.3, 6.2, 2.6],
            }
        )

        exp = pd.DataFrame(
            {
                "timestamp": ["2013-03-17 10:34:00", "2013-03-17 10:34:30"],
                "dev1_co": [np.nan, np.nan],
                "dev1_co2": [2.3, 2.6],
                "dev1_no2": [6.2, np.nan],
                "dev1_o3": [np.nan, np.nan],
            }
        )
        exp = exp.set_index(["timestamp"])
        exp.columns.name = "measurand"
        res = daily_preprocessing.long_to_wide(
            example_data, measurands=["co", "o3", "co2", "no2"]
        )
        pd.testing.assert_frame_equal(res, exp)

    def test_different_types(self):
        # CO2 has both float and string values, which shouldn't happen following
        # the QA part of the scraping script, but best to check
        example_data = pd.DataFrame(
            {
                "timestamp": [
                    "2013-03-17 10:34:00",
                    "2013-03-17 10:34:00",
                    "2013-03-17 10:34:30",
                ],
                "device": ["dev1", "dev1", "dev1"],
                "measurand": ["co2", "no2", "co2"],
                "value": [2.3, 6.2, "3.2"],
            }
        )

        with self.assertRaises(utils.DataConversionError):
            res = daily_preprocessing.long_to_wide(
                example_data, measurands=["co", "o3", "co2", "no2"]
            )

    def test_missing_columns1(self):
        # Missing timestamp column
        example_data = pd.DataFrame(
            {
                "device": ["dev1", "dev1", "dev1"],
                "measurand": ["co2", "no2", "co2"],
                "value": [2.3, 6.2, "3.2"],
            }
        )

        with self.assertRaises(utils.DataConversionError):
            res = daily_preprocessing.long_to_wide(
                example_data, measurands=["co", "o3", "co2", "no2"]
            )

    def test_missing_columns2(self):
        # Missing device column
        example_data = pd.DataFrame(
            {
                "timestamp": [
                    "2013-03-17 10:34:00",
                    "2013-03-17 10:34:00",
                    "2013-03-17 10:34:30",
                ],
                "measurand": ["co2", "no2", "co2"],
                "value": [2.3, 6.2, "3.2"],
            }
        )

        with self.assertRaises(utils.DataConversionError):
            res = daily_preprocessing.long_to_wide(
                example_data, measurands=["co", "o3", "co2", "no2"]
            )

    def test_missing_columns3(self):
        # Missing measurand column
        example_data = pd.DataFrame(
            {
                "timestamp": [
                    "2013-03-17 10:34:00",
                    "2013-03-17 10:34:00",
                    "2013-03-17 10:34:30",
                ],
                "device": ["dev1", "dev1", "dev1"],
                "value": [2.3, 6.2, "3.2"],
            }
        )

        with self.assertRaises(utils.DataConversionError):
            res = daily_preprocessing.long_to_wide(
                example_data, measurands=["co", "o3", "co2", "no2"]
            )

    def test_missing_columns4(self):
        # Missing value column
        example_data = pd.DataFrame(
            {
                "timestamp": [
                    "2013-03-17 10:34:00",
                    "2013-03-17 10:34:00",
                    "2013-03-17 10:34:30",
                ],
                "device": ["dev1", "dev1", "dev1"],
                "measurand": ["co2", "no2", "co2"],
            }
        )

        with self.assertRaises(utils.DataConversionError):
            res = daily_preprocessing.long_to_wide(
                example_data, measurands=["co", "o3", "co2", "no2"]
            )

    def test_no_rows_no_measurands(self):
        # Test when have no clean data and haven't specified measurands
        # that must be present. Should return an empty data frame
        example_data = pd.DataFrame(
            {"timestamp": [], "device": [], "measurand": [], "value": [],}
        )

        exp = pd.DataFrame(dtype=np.float64)
        idx = pd.Index([])
        idx.set_names("timestamp", inplace=True)
        exp.index = idx
        exp.columns = pd.MultiIndex.from_tuples([], names=[None, "measurand"])

        res = daily_preprocessing.long_to_wide(example_data)

        # Check output data frame is empty
        self.assertTrue(res.empty)

        # Check it's got the same column and index types as expected
        pd.testing.assert_frame_equal(
            res, exp, check_column_type=False, check_index_type=False
        )

    def test_no_rows_with_measurands(self):
        # Test when have no clean data but have specified measurands,
        # should still get an empty data frame but with specified columns
        example_data = pd.DataFrame(
            {"timestamp": [], "device": [], "measurand": [], "value": [],}
        )

        exp = pd.DataFrame(dtype=np.float64)
        idx = pd.Index([])
        idx.set_names("timestamp", inplace=True)
        exp.index = idx
        exp.columns = pd.MultiIndex.from_tuples([], names=[None, "measurand"])

        res = daily_preprocessing.long_to_wide(example_data)

        # Check output data frame is empty
        self.assertTrue(res.empty)

        # Check it's got the same column and index types as expected
        pd.testing.assert_frame_equal(
            res, exp, check_column_type=False, check_index_type=False
        )


class TestResample(unittest.TestCase):
    # Tests daily_preprocessing.resample() function,
    # which is a wrapper around pandas.resample()

    def test_success_1min(self):
        dummy = pd.DataFrame(
            {
                "timestamp": [
                    "2013-03-17 10:31:00",
                    "2013-03-17 10:31:30",
                    "2013-03-17 10:31:40",
                    "2013-03-17 10:32:00",
                    "2013-03-17 10:33:00",
                    "2013-03-17 10:33:14",
                    "2013-03-17 10:33:59",
                    "2013-03-17 10:34:00",
                ],
                "measurand1": np.arange(8),
                "measurand2": np.arange(10, 18) * 2,
            }
        )
        dummy["timestamp"] = pd.to_datetime(dummy["timestamp"])
        dummy.set_index("timestamp", inplace=True)

        res = daily_preprocessing.resample(dummy, "1Min")

        exp = pd.DataFrame(
            {
                "timestamp": [
                    "2013-03-17 10:31:00",
                    "2013-03-17 10:32:00",
                    "2013-03-17 10:33:00",
                    "2013-03-17 10:34:00",
                ],
                "measurand1": [1, 3, 5, 7],
                "measurand2": [22, 26, 30, 34],
            }
        )
        exp["timestamp"] = pd.to_datetime(exp["timestamp"])
        exp.set_index("timestamp", inplace=True)

        pd.testing.assert_frame_equal(res, exp)

    def test_success_1min_with_missing(self):
        # Test handles missing minutes, which should be given NaN
        dummy = pd.DataFrame(
            {
                "timestamp": [
                    "2013-03-17 10:31:00",
                    "2013-03-17 10:31:30",
                    "2013-03-17 10:31:40",
                    "2013-03-17 10:33:00",
                    "2013-03-17 10:33:14",
                    "2013-03-17 10:33:59",
                    "2013-03-17 10:34:00",
                ],
                "measurand1": np.arange(7),
                "measurand2": np.arange(10, 17) * 2,
            }
        )
        dummy["timestamp"] = pd.to_datetime(dummy["timestamp"])
        dummy.set_index("timestamp", inplace=True)

        res = daily_preprocessing.resample(dummy, "1Min")

        exp = pd.DataFrame(
            {
                "timestamp": [
                    "2013-03-17 10:31:00",
                    "2013-03-17 10:32:00",
                    "2013-03-17 10:33:00",
                    "2013-03-17 10:34:00",
                ],
                "measurand1": [1, np.nan, 4, 6],
                "measurand2": [22, np.nan, 28, 32],
            }
        )
        exp["timestamp"] = pd.to_datetime(exp["timestamp"])
        exp.set_index("timestamp", inplace=True)

        pd.testing.assert_frame_equal(res, exp)

    def test_success_1hour_with_missing(self):
        # Test that summarises by hour, and adds NaN for any missing hour
        dummy = pd.DataFrame(
            {
                "timestamp": [
                    "2013-03-17 10:31:00",
                    "2013-03-17 10:31:30",
                    "2013-03-17 10:31:40",
                    "2013-03-17 11:29:17",
                    "2013-03-17 11:29:17",
                    "2013-03-17 12:00:00",
                    "2013-03-17 14:58:59",
                    "2013-03-17 14:28:02",
                ],
                "measurand1": np.arange(8),
                "measurand2": np.arange(10, 18) * 2,
            }
        )
        dummy["timestamp"] = pd.to_datetime(dummy["timestamp"])
        dummy.set_index("timestamp", inplace=True)

        res = daily_preprocessing.resample(dummy, "1H")

        exp = pd.DataFrame(
            {
                "timestamp": [
                    "2013-03-17 10:00:00",
                    "2013-03-17 11:00:00",
                    "2013-03-17 12:00:00",
                    "2013-03-17 13:00:00",
                    "2013-03-17 14:00:00",
                ],
                "measurand1": [1, 3.5, 5, np.nan, 6.5],
                "measurand2": [22, 27, 30, np.nan, 33],
            }
        )
        exp["timestamp"] = pd.to_datetime(exp["timestamp"])
        exp.set_index("timestamp", inplace=True)

        pd.testing.assert_frame_equal(res, exp)

    def test_error_notimeindex(self):
        # resample method requires index to be a datetime object
        # Don't explicitly set timestamp to be datetime, or as index here
        dummy = pd.DataFrame(
            {
                "timestamp": [
                    "2013-03-17 10:31:00",
                    "2013-03-17 10:31:30",
                    "2013-03-17 10:31:40",
                    "2013-03-17 10:32:00",
                    "2013-03-17 10:33:00",
                    "2013-03-17 10:33:14",
                    "2013-03-17 10:33:59",
                    "2013-03-17 10:34:00",
                ],
                "measurand1": np.arange(8),
                "measurand2": np.arange(10, 18) * 2,
            }
        )

        with self.assertRaises(utils.ResamplingError):
            res = daily_preprocessing.resample(dummy, "1Min")

    def test_error_bad_resolution_format(self):
        # Should raise error when pass in invalid time format
        dummy = pd.DataFrame(
            {
                "timestamp": [
                    "2013-03-17 10:31:00",
                    "2013-03-17 10:31:30",
                    "2013-03-17 10:31:40",
                    "2013-03-17 10:32:00",
                    "2013-03-17 10:33:00",
                    "2013-03-17 10:33:14",
                    "2013-03-17 10:33:59",
                    "2013-03-17 10:34:00",
                ],
                "measurand1": np.arange(8),
                "measurand2": np.arange(10, 18) * 2,
            }
        )
        dummy["timestamp"] = pd.to_datetime(dummy["timestamp"])
        dummy.set_index("timestamp", inplace=True)

        with self.assertRaises(utils.ResamplingError):
            res = daily_preprocessing.resample(dummy, "adsdsa")


if __name__ == "__main__":
    unittest.main()
