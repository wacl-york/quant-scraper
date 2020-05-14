"""
    test_preprocessing.py
    ~~~~~~~~~~~~~~~~~~~~~

    Unit tests for the quantscraper/daily_preprocessing.py script.
"""

import unittest
from unittest.mock import patch, Mock, mock_open
import pandas as pd
import json
import numpy as np
import datetime
import configparser
import quantscraper.utils as utils
import quantscraper.daily_preprocessing as daily_preprocessing


class TestLoadData(unittest.TestCase):
    def test_success(self):
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
        with patch("quantscraper.daily_preprocessing.pd") as mock_pd:
            mock_read = Mock(return_value=example_data)
            mock_pd.read_csv = mock_read
            mock_todt = Mock(return_value=timestamp_dt)
            mock_pd.to_datetime = mock_todt

            res = daily_preprocessing.get_data(
                "cleanfoo", "manu1", "dev1", "2012-03-12"
            )
            print(res)
            print(exp)

            # Format of expected filename is given in utils.CLEAN_DATA_FN
            mock_read.assert_called_once_with("cleanfoo/manu1_dev1_2012-03-12.csv")

            # Need to use pandas built-in function for asserting data frame
            # equality
            pd.testing.assert_frame_equal(res, exp)

    # Test for FileNotFoundError, but cannot mock
    # pd.errors.EmptyDataError
    def test_file_not_found(self):
        # Mock file I/O
        with patch("quantscraper.daily_preprocessing.pd") as mock_pd:
            mock_read = Mock(side_effect=FileNotFoundError(""))
            mock_pd.read_csv = mock_read

            with self.assertRaises(utils.DataReadingError):
                res = daily_preprocessing.get_data(
                    "cleanfoo", "manu1", "dev1", "2012-03-12"
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
                "co2_dev1": [2.3, 2.6],
                "no2_dev1": [6.2, np.nan],
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
                "co2_dev1": [2.3, 2.6],
                "co_dev1": [np.nan, np.nan],
                "no2_dev1": [6.2, np.nan],
                "o3_dev1": [np.nan, np.nan],
            }
        )
        exp = exp.set_index(["timestamp"])
        exp.columns.name = "measurand"
        res = daily_preprocessing.long_to_wide(
            example_data, measurands=["co", "o3", "co2", "no2"]
        )
        pd.testing.assert_frame_equal(res, exp)

    def test_adds_missing_devices(self):
        # Have CO2 and NO2 at first timestamp, from both devices, but only CO2
        # at first from second device, so should add no2_dev2 column filled
        # with NaNs and second CO2 timepoint should be NaN
        # Will also ask for a third device that don't have any measurements from
        example_data = pd.DataFrame(
            {
                "timestamp": [
                    "2013-03-17 10:34:00",
                    "2013-03-17 10:34:00",
                    "2013-03-17 10:34:00",
                    "2013-03-17 10:34:30",
                    "2013-03-17 10:34:30",
                ],
                "device": ["dev1", "dev1", "dev2", "dev1", "dev1"],
                "measurand": ["co2", "no2", "co2", "co2", "no2"],
                "value": [2.3, 6.2, 2.6, 5.2, -23],
            }
        )

        exp = pd.DataFrame(
            {
                "timestamp": ["2013-03-17 10:34:00", "2013-03-17 10:34:30"],
                "co2_dev1": [2.3, 5.2],
                "co2_dev2": [2.6, np.nan],
                "co2_dev3": [np.nan, np.nan],
                "no2_dev1": [6.2, -23],
                "no2_dev2": [np.nan, np.nan],
                "no2_dev3": [np.nan, np.nan],
            }
        )
        exp = exp.set_index(["timestamp"])
        exp.columns.name = "measurand"
        res = daily_preprocessing.long_to_wide(
            example_data, devices=["dev1", "dev2", "dev3"]
        )
        pd.testing.assert_frame_equal(res, exp)

    def test_adds_missing_devices_and_measurands(self):
        # Specify both measurands and devices that should be included in output
        # Have CO2 and NO2 at first timestamp, from both devices, but only CO2
        # at first from second device, so should add no2_dev2 column filled
        # with NaNs and second CO2 timepoint should be NaN
        # Will also ask for a third device that don't have any measurements from
        # Also specifying which measurands should be included, will have a mix
        # of some that don't have any recordings at all and some that have some
        # recordings
        example_data = pd.DataFrame(
            {
                "timestamp": [
                    "2013-03-17 10:34:00",
                    "2013-03-17 10:34:00",
                    "2013-03-17 10:34:00",
                    "2013-03-17 10:34:30",
                    "2013-03-17 10:34:30",
                    "2013-03-17 10:34:30",
                ],
                "device": ["dev1", "dev1", "dev2", "dev1", "dev1", "dev2"],
                "measurand": ["co2", "no2", "co2", "co2", "no2", "co"],
                "value": [2.3, 6.2, 2.6, 5.2, -23, 23.84],
            }
        )

        exp = pd.DataFrame(
            {
                "timestamp": ["2013-03-17 10:34:00", "2013-03-17 10:34:30"],
                "co2_dev1": [2.3, 5.2],
                "co2_dev2": [2.6, np.nan],
                "co2_dev3": [np.nan, np.nan],
                "co_dev1": [np.nan, np.nan],
                "co_dev2": [np.nan, 23.84],
                "co_dev3": [np.nan, np.nan],
                "no2_dev1": [6.2, -23],
                "no2_dev2": [np.nan, np.nan],
                "no2_dev3": [np.nan, np.nan],
                "o3_dev1": [np.nan, np.nan],
                "o3_dev2": [np.nan, np.nan],
                "o3_dev3": [np.nan, np.nan],
            }
        )
        exp = exp.set_index(["timestamp"])
        exp.columns.name = "measurand"
        res = daily_preprocessing.long_to_wide(
            example_data,
            devices=["dev1", "dev2", "dev3"],
            measurands=["co", "o3", "co2", "no2"],
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
            res = daily_preprocessing.long_to_wide(example_data)

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
            res = daily_preprocessing.long_to_wide(example_data)

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
            res = daily_preprocessing.long_to_wide(example_data)

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
            res = daily_preprocessing.long_to_wide(example_data)

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
            res = daily_preprocessing.long_to_wide(example_data)

    def test_no_rows_no_measurands_or_devices(self):
        # Test when have no clean data and haven't specified measurands
        # or devices that must be present. Should return an empty data frame
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
        # Should still get an empty data frame with 0 columns,
        # because there are no available devices to use to form
        # the <device_measurand> column name
        example_data = pd.DataFrame(
            {"timestamp": [], "device": [], "measurand": [], "value": [],}
        )

        exp = pd.DataFrame(dtype=np.float64)
        idx = pd.Index([])
        idx.set_names("timestamp", inplace=True)
        exp.index = idx
        exp.columns = pd.MultiIndex.from_tuples([], names=[None, "measurand"])

        res = daily_preprocessing.long_to_wide(
            example_data, measurands=["co2", "co", "no2"]
        )

        # Check output data frame is empty
        self.assertTrue(res.empty)

        # Check it's got the same column and index types as expected
        pd.testing.assert_frame_equal(
            res, exp, check_column_type=False, check_index_type=False
        )

    def test_no_rows_with_devices(self):
        # Test when have no clean data but have specified devices,
        # Should still get an empty data frame with 0 columns,
        # because there are no available measurands to use to form
        # the <device_measurand> column name
        example_data = pd.DataFrame(
            {"timestamp": [], "device": [], "measurand": [], "value": [],}
        )

        exp = pd.DataFrame(dtype=np.float64)
        idx = pd.Index([])
        idx.set_names("timestamp", inplace=True)
        exp.index = idx
        exp.columns = pd.MultiIndex.from_tuples([], names=[None, "measurand"])

        res = daily_preprocessing.long_to_wide(example_data, devices=["dev1", "dev2"])

        # Check output data frame is empty
        self.assertTrue(res.empty)

        # Check it's got the same column and index types as expected
        pd.testing.assert_frame_equal(
            res, exp, check_column_type=False, check_index_type=False
        )

    def test_no_rows_with_devices_and_measurands(self):
        # Test when have no clean data but have specified devices and
        # measurands.
        # Should still get an empty data frame but now as both devices
        # and measurands are specified should get the required columns
        example_data = pd.DataFrame(
            {"timestamp": [], "device": [], "measurand": [], "value": [],}
        )

        # Setting up an empty data frame with specific columns is quite
        # convoluted in pandas, especially as assert_frame_equal() is very
        # through.
        # Need to firstly set the index to 'timestamp' (not required by pandas
        # but the expected output has this index), then also need to provide
        # a 'MultiIndex' for the output columns with name 'measurand'

        idx = pd.Index([])
        idx.set_names("timestamp", inplace=True)
        exp = pd.DataFrame(
            {
                "co2_dev1": float(),
                "co2_dev2": float(),
                "no2_dev1": float(),
                "no2_dev2": float(),
            },
            index=idx,
        )
        exp.columns = pd.MultiIndex.from_tuples(
            [("co2_dev1", ""), ("co2_dev2", ""), ("no2_dev1", ""), ("no2_dev2", "")],
            names=[None, "measurand"],
        )

        res = daily_preprocessing.long_to_wide(
            example_data, devices=["dev1", "dev2"], measurands=["no2", "co2"]
        )

        # Check output data frame is empty
        self.assertTrue(res.empty)

        # Check it's got the same column and index types as expected
        pd.testing.assert_frame_equal(
            res, exp, check_column_type=True, check_index_type=False
        )

    # TODO Add tests for when devices are specified, and also for devices +
    # manufacturer


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


class TestSetupScrapingTimeframe(unittest.TestCase):
    def test_no_date(self):
        # Don't pass in date, so output should have yesterday's date
        cfg = configparser.ConfigParser()
        cfg.add_section("Analysis")
        cfg.set("Analysis", "foo", "bar")

        # Mock date.today() to a fixed date
        with patch("quantscraper.daily_preprocessing.date", autospec=True) as mock_date:
            mock_today = Mock(return_value=datetime.date(2012, 3, 17))
            mock_date.today = mock_today

            res = daily_preprocessing.setup_scraping_timeframe(cfg)
            self.assertEqual(res, "2012-03-16")

    def test_date_provided(self):
        # Providing config with valid date attribute shouldn't modify it
        cfg = configparser.ConfigParser()
        cfg.add_section("Analysis")
        cfg.set("Analysis", "foo", "bar")
        cfg.set("Analysis", "date", "2019-05-23")
        res = daily_preprocessing.setup_scraping_timeframe(cfg)
        self.assertEqual(res, "2019-05-23")

    def test_invalid_date(self):
        # Date is provided, but isn't in YYYY-mm-dd format so should raise error
        cfg = configparser.ConfigParser()
        cfg.add_section("Analysis")
        cfg.set("Analysis", "foo", "bar")
        cfg.set("Analysis", "date", "2020/03/04")

        with self.assertRaises(utils.TimeError):
            daily_preprocessing.setup_scraping_timeframe(cfg)

    def test_zeropadding_added(self):
        # Valid date is provided but doesn't have zero padding, which is always
        # present in the clean data filenames
        cfg = configparser.ConfigParser()
        cfg.add_section("Analysis")
        cfg.set("Analysis", "foo", "bar")
        cfg.set("Analysis", "date", "2020-3-4")

        res = daily_preprocessing.setup_scraping_timeframe(cfg)
        self.assertEqual(res, "2020-03-04")


if __name__ == "__main__":
    unittest.main()
