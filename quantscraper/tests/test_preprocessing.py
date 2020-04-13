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
        exp["manufacturer"] = "manu1"
        exp["device"] = "dev1"

        # Mock file I/O
        with patch("daily_preprocessing.pd") as mock_pd:
            mock_read = Mock(return_value=example_data)
            mock_pd.read_csv = mock_read

            res = daily_preprocessing.get_data(
                cfg, "manu1", "dev1", "2012-03-12 10:23:55", "2012-04-12 10:56:09"
            )

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
                "manufacturer": ["manu1", "manu1", "manu1"],
                "device": ["dev1", "dev1", "dev1"],
                "measurand": ["co2", "no2", "co2"],
                "value": [2.3, 6.2, 2.6],
            }
        )

        exp = pd.DataFrame(
            {
                "manufacturer": ["manu1", "manu1"],
                "device": ["dev1", "dev1"],
                "timestamp": ["2013-03-17 10:34:00", "2013-03-17 10:34:30"],
                "co2": [2.3, 2.6],
                "no2": [6.2, np.nan],
            }
        )
        exp = exp.set_index(["manufacturer", "device", "timestamp"])
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
                "manufacturer": ["manu1", "manu1", "manu1"],
                "device": ["dev1", "dev1", "dev1"],
                "measurand": ["co2", "no2", "co2"],
                "value": [2.3, 6.2, 2.6],
            }
        )

        exp = pd.DataFrame(
            {
                "manufacturer": ["manu1", "manu1"],
                "device": ["dev1", "dev1"],
                "timestamp": ["2013-03-17 10:34:00", "2013-03-17 10:34:30"],
                "co2": [2.3, 2.6],
                "no2": [6.2, np.nan],
                "co": [np.nan, np.nan],
                "o3": [np.nan, np.nan],
            }
        )
        exp = exp.set_index(["manufacturer", "device", "timestamp"])
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
                "manufacturer": ["manu1", "manu1", "manu1"],
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
        # Missing manufacturer column
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

    def test_missing_columns2(self):
        # Missing timestamp column
        example_data = pd.DataFrame(
            {
                "manufacturer": ["manu1", "manu1", "manu1"],
                "device": ["dev1", "dev1", "dev1"],
                "measurand": ["co2", "no2", "co2"],
                "value": [2.3, 6.2, "3.2"],
            }
        )

        with self.assertRaises(utils.DataConversionError):
            res = daily_preprocessing.long_to_wide(
                example_data, measurands=["co", "o3", "co2", "no2"]
            )

    def test_missing_columns3(self):
        # Missing device column
        example_data = pd.DataFrame(
            {
                "timestamp": [
                    "2013-03-17 10:34:00",
                    "2013-03-17 10:34:00",
                    "2013-03-17 10:34:30",
                ],
                "manufacturer": ["manu1", "manu1", "manu1"],
                "measurand": ["co2", "no2", "co2"],
                "value": [2.3, 6.2, "3.2"],
            }
        )

        with self.assertRaises(utils.DataConversionError):
            res = daily_preprocessing.long_to_wide(
                example_data, measurands=["co", "o3", "co2", "no2"]
            )

    def test_missing_columns4(self):
        # Missing measurand column
        example_data = pd.DataFrame(
            {
                "timestamp": [
                    "2013-03-17 10:34:00",
                    "2013-03-17 10:34:00",
                    "2013-03-17 10:34:30",
                ],
                "manufacturer": ["manu1", "manu1", "manu1"],
                "device": ["dev1", "dev1", "dev1"],
                "value": [2.3, 6.2, "3.2"],
            }
        )

        with self.assertRaises(utils.DataConversionError):
            res = daily_preprocessing.long_to_wide(
                example_data, measurands=["co", "o3", "co2", "no2"]
            )

    def test_missing_columns5(self):
        # Missing value column
        example_data = pd.DataFrame(
            {
                "timestamp": [
                    "2013-03-17 10:34:00",
                    "2013-03-17 10:34:00",
                    "2013-03-17 10:34:30",
                ],
                "manufacturer": ["manu1", "manu1", "manu1"],
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
            {
                "timestamp": [],
                "manufacturer": [],
                "device": [],
                "measurand": [],
                "value": [],
            }
        )

        exp = pd.DataFrame(dtype=np.float64)
        exp.index = pd.MultiIndex.from_tuples(
            [], names=["manufacturer", "device", "timestamp"]
        )
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
            {
                "timestamp": [],
                "manufacturer": [],
                "device": [],
                "measurand": [],
                "value": [],
            }
        )

        exp = pd.DataFrame(dtype=np.float64)
        exp.index = pd.MultiIndex.from_tuples(
            [], names=["manufacturer", "device", "timestamp"]
        )
        exp.columns = pd.MultiIndex.from_tuples([], names=[None, "measurand"])

        res = daily_preprocessing.long_to_wide(example_data)

        # Check output data frame is empty
        self.assertTrue(res.empty)

        # Check it's got the same column and index types as expected
        pd.testing.assert_frame_equal(
            res, exp, check_column_type=False, check_index_type=False
        )


if __name__ == "__main__":
    unittest.main()
