"""
    test_cli.py
    ~~~~~~~~~~~

    Unit tests for cli functions.
"""

from datetime import date
import unittest
from collections import defaultdict
import logging
import os
from unittest.mock import patch, MagicMock, Mock, call

import quantscraper.cli as cli
import quantscraper.utils as utils
from utils import build_mock_today
from quantscraper.manufacturers.Manufacturer import Device
import quantscraper.manufacturers.Aeroqual as Aeroqual

# Setup dummy env variables
os.environ["AEROQUAL_USER"] = "foo"
os.environ["AEROQUAL_PW"] = "foo"
os.environ["AQMESH_USER"] = "foo"
os.environ["AQMESH_PW"] = "foo"
os.environ["ZEPHYR_USER"] = "foo"
os.environ["ZEPHYR_PW"] = "foo"
os.environ["QUANTAQ_API_TOKEN"] = "foo"


class TestSetupLoggers(unittest.TestCase):
    # Capturing the log output is relatively tricky without a 3rd party library.
    # This would be ideal to check that the log format is as expected, but not
    # worth the additional dependency and test complexity for now.
    # Instead will just ensure the setup is as expected.

    def test_logger(self):
        # By default, logger is set to warn (30) and has no handlers
        logger = logging.getLogger()
        self.assertEqual(logger.getEffectiveLevel(), 30)

        # After running cli.seutp_loggers, the CLI logger should be set to
        # record at INFO (20) and has handlers
        cli.setup_loggers(None)
        logger = logging.getLogger("cli")
        self.assertEqual(logger.getEffectiveLevel(), 20)
        self.assertTrue(logger.hasHandlers())

    def test_formatter(self):
        # Can't easily capture log output so instead will ensure that the
        # formatter is setup as expected
        with patch("quantscraper.cli.logging") as mock_logging:
            # Mock the Formatter function that builds a format object
            mock_fmt = Mock()
            mock_formatter = MagicMock(return_value=mock_fmt)
            mock_logging.Formatter = mock_formatter

            # Mock the setFormatter setter to ensure that it is called with the
            # returned format object
            mock_setformatter = Mock()
            mock_logging.StreamHandler.return_value.setFormatter = mock_setformatter

            cli.setup_loggers(None)
            mock_formatter.assert_called_once_with(
                "%(asctime)-8s:%(levelname)s: %(message)s", datefmt="%Y-%m-%d,%H:%M:%S"
            )
            mock_setformatter.assert_called_once_with(mock_fmt)


class TestParseArgs(unittest.TestCase):
    def test_success(self):
        # Just confirm that expected calls are made
        with patch("quantscraper.cli.argparse.ArgumentParser") as mock_ArgumentParser:
            mock_addargument = Mock()
            mock_args = Mock
            mock_parseargs = Mock(return_value=mock_args)
            mock_parser = Mock(add_argument=mock_addargument, parse_args=mock_parseargs)
            mock_ArgumentParser.return_value = mock_parser

            res = cli.parse_args()

            self.assertEqual(res, mock_args)
            mock_ArgumentParser.assert_called_once_with(description="QUANT scraper")

            actual_addargument_calls = mock_addargument.mock_calls
            exp_addargument_calls = [
                call(
                    "--devices",
                    metavar="DEVICE1 DEVICE2 ... DEVICEN",
                    nargs="+",
                    help="Specify the device IDs to include in the scraping. If not provided then all the devices specified in the configuration file are scraped.",
                ),
                call(
                    "--start",
                    metavar="DATE",
                    help="The earliest date to download data for (inclusive). Must be in the format YYYY-mm-dd. Defaults to the previous day.",
                ),
                call(
                    "--end",
                    metavar="DATE",
                    help="The latest date to download data for (inclusive). Must be in the format YYYY-mm-dd. Defaults to the previous day.",
                ),
                call(
                    "--save-raw",
                    action="store_true",
                    help="Saves raw data to local file storage. Required in order to later upload to GoogleDrive.",
                ),
                call(
                    "--save-clean",
                    action="store_true",
                    help="Saves clean data to local file storage. Required in order to later upload to GoogleDrive.",
                ),
                call(
                    "--upload-raw",
                    action="store_true",
                    help="Uploads raw data to Google Drive. Data must be either already available locally, or saved during the run with the save-raw flag.",
                ),
                call(
                    "--upload-clean",
                    action="store_true",
                    help="Uploads clean data to Google Drive. Data must be either already available locally, or saved during the run with the save-clean flag.",
                ),
                call(
                    "--html",
                    metavar="FN",
                    help="A filename to save an HTML summary to. If not provided then no HTML summary is produced.",
                ),
            ]
            self.assertEqual(actual_addargument_calls, exp_addargument_calls)

            mock_parseargs.assert_called_once_with()


class TestSetupScrapingTimeframe(unittest.TestCase):
    def test_no_start_end_times(self):
        # Don't pass in start time or end time, so the output time should be
        # yesterday midnight to 1 second before following midnight
        with patch("quantscraper.cli.date", build_mock_today(2012, 3, 17)):
            start, end = cli.setup_scraping_timeframe()

            # assert cfg times are as expected, as this function modifies cfg by
            # reference rather than returning it directly
            self.assertEqual(start, date(2012, 3, 16))
            self.assertEqual(end, date(2012, 3, 16))

    def test_no_end_time(self):
        # Don't pass in end time, so the output time should be
        # specified time to 1 second before today's midnight

        with patch("quantscraper.cli.date", build_mock_today(2012, 3, 16)):
            start, end = cli.setup_scraping_timeframe(start="2012-02-28")

            # assert cfg times are as expected, as this function modifies cfg by
            # reference rather than returning it directly
            self.assertEqual(start, date(2012, 2, 28))
            self.assertEqual(end, date(2012, 3, 15))

    def test_no_start_time(self):
        # Don't pass in start time, so the output time should be
        # yesterday's midnight to specified end time

        with patch("quantscraper.cli.date", build_mock_today(2035, 10, 12)):
            start, end = cli.setup_scraping_timeframe(end="2035-10-12")

            # assert cfg times are as expected, as this function modifies cfg by
            # reference rather than returning it directly
            self.assertEqual(start, date(2035, 10, 11))
            self.assertEqual(end, date(2035, 10, 12))

    def test_both_times_specified(self):
        # Both start and end times are specified in config file
        with patch("quantscraper.cli.date", build_mock_today(2035, 10, 12)):
            start, end = cli.setup_scraping_timeframe(
                start="2035-10-11", end="2035-10-12"
            )

            self.assertEqual(start, date(2035, 10, 11))
            self.assertEqual(end, date(2035, 10, 12))

    def test_start_later_end_both_passed_in(self):
        # Here start date is later than end. Shouldn't be allowed!
        # Here both are passed in

        with patch("quantscraper.cli.date", build_mock_today(2035, 10, 12)):
            with self.assertRaises(utils.TimeError):
                cli.setup_scraping_timeframe(start="2035-10-13", end="2035-10-12")

    def test_start_later_end_start_assumed(self):
        # Here start date is later than end. Shouldn't be allowed!
        # Here just the end date is passed in and start date is taken as default

        with patch("quantscraper.cli.date", build_mock_today(2019, 8, 17)):
            with self.assertRaises(utils.TimeError):
                cli.setup_scraping_timeframe(end="2019-08-15")

    def test_start_later_end_end_assumed(self):
        # Here start date is later than end. Shouldn't be allowed!
        # Here just the start date is passed in and end date is taken as default
        with patch("quantscraper.cli.date", build_mock_today(2019, 8, 17)):
            with self.assertRaises(utils.TimeError):
                cli.setup_scraping_timeframe(start="2019-08-17")

    def test_start_equal_end_both_passed_in(self):
        # Here start date is equal to end.
        # Here both are passed in
        with patch("quantscraper.cli.date", build_mock_today(2019, 8, 17)):
            start, end = cli.setup_scraping_timeframe(
                start="2035-10-13", end="2035-10-13"
            )
            self.assertEqual(start, date(2035, 10, 13))
            self.assertEqual(end, date(2035, 10, 13))

    def test_start_equal_end_start_assumed(self):
        # Here start date is equal to end.
        # Here just the end date is passed in and start date is taken as default
        with patch("quantscraper.cli.date", build_mock_today(2019, 8, 17)):
            start, end = cli.setup_scraping_timeframe(end="2019-08-16")
            self.assertEqual(start, date(2019, 8, 16))
            self.assertEqual(end, date(2019, 8, 16))

    def test_start_equal_end_end_assumed(self):
        # Here start date is equal to end.
        # Here just the start date is passed in and end date is taken as default
        with patch("quantscraper.cli.date", build_mock_today(2019, 8, 17)):
            start, end = cli.setup_scraping_timeframe(start="2019-08-16")
            self.assertEqual(start, date(2019, 8, 16))
            self.assertEqual(end, date(2019, 8, 16))

    def test_formatting_error_start(self):
        # Pass in a poorly specified time format to start time
        with patch("quantscraper.cli.date", build_mock_today(2019, 8, 17)):
            with self.assertRaises(utils.TimeError):
                cli.setup_scraping_timeframe(start="2012/03/04")


class TestScrape(unittest.TestCase):
    # Tests the scrape() function, which iterates through a given manufacturer's
    # devices and scrapes their data

    def test_success_all_ids(self):
        # Test success on all devices
        mock_scrape = Mock(side_effect=["foo", "bar", "cat"])
        man = Mock(scrape_device=mock_scrape,)
        dev1 = Device("1", "4", "foo")
        dev2 = Device("2", "5", "foo")
        dev3 = Device("3", "6", "foo")
        man.devices = [dev1, dev2, dev3]
        mock_start = MagicMock()
        mock_end = MagicMock()

        with self.assertLogs(level="INFO") as cm:
            cli.scrape(man, mock_start, mock_end)

        # Assert log is called with expected messages
        self.assertEqual(
            cm.output,
            [
                "INFO:root:Download successful for device 1.",
                "INFO:root:Download successful for device 2.",
                "INFO:root:Download successful for device 3.",
            ],
        )

        # Assert scrape calls are as expected
        scrape_calls = mock_scrape.mock_calls
        exp_calls = [
            call("4", mock_start, mock_end),
            call("5", mock_start, mock_end),
            call("6", mock_start, mock_end),
        ]
        self.assertEqual(scrape_calls, exp_calls)

        # And that the raw data fields are set accordingly
        self.assertEqual(dev1.raw_data, "foo")
        self.assertEqual(dev2.raw_data, "bar")
        self.assertEqual(dev3.raw_data, "cat")

    def test_mixed_success(self):
        # 2nd device raises utils.DataDownloadError
        mock_scrape = Mock(side_effect=["foo", utils.DataDownloadError(""), "cat"])
        man = Mock(scrape_device=mock_scrape,)

        dev1 = Device("1", "4", "foo")
        dev2 = Device("2", "5", "foo")
        dev3 = Device("3", "6", "foo")
        man.devices = [dev1, dev2, dev3]
        mock_start = MagicMock()
        mock_end = MagicMock()

        with self.assertLogs(level="INFO") as cm:
            cli.scrape(man, mock_start, mock_end)

        # Assert log is called with expected messages
        # NB: using assertIn rather than assertEqual as hard to produce the
        # expected stacktrace that will also be logged alongside the error
        # message.
        self.assertIn("INFO:root:Download successful for device 1.", cm.output)
        self.assertIn("ERROR:root:Unable to download data for device 2.", cm.output)
        self.assertIn("INFO:root:Download successful for device 3.", cm.output)

        # Assert scrape calls are as expected
        scrape_calls = mock_scrape.mock_calls
        exp_calls = [
            call("4", mock_start, mock_end),
            call("5", mock_start, mock_end),
            call("6", mock_start, mock_end),
        ]
        self.assertEqual(scrape_calls, exp_calls)

        # And that the raw data fields are set accordingly
        self.assertEqual(dev1.raw_data, "foo")
        self.assertEqual(dev2.raw_data, None)
        self.assertEqual(dev3.raw_data, "cat")

    def test_all_failure(self):
        # all devices fail to download data
        mock_scrape = Mock(
            side_effect=[
                utils.DataDownloadError(""),
                utils.DataDownloadError(""),
                utils.DataDownloadError(""),
            ]
        )
        man = Mock(scrape_device=mock_scrape,)
        dev1 = Device("1", "4", "foo")
        dev2 = Device("2", "5", "foo")
        dev3 = Device("3", "6", "foo")
        mock_start = MagicMock()
        mock_end = MagicMock()
        man.devices = [dev1, dev2, dev3]

        with self.assertLogs(level="INFO") as cm:
            cli.scrape(man, mock_start, mock_end)

        # Assert log is called with expected messages
        # NB: using assertIn rather than assertEqual as hard to produce the
        # expected stacktrace that will also be logged alongside the error
        # message.
        self.assertIn("ERROR:root:Unable to download data for device 1.", cm.output)
        self.assertIn("ERROR:root:Unable to download data for device 2.", cm.output)
        self.assertIn("ERROR:root:Unable to download data for device 3.", cm.output)

        # Assert scrape calls are as expected
        scrape_calls = mock_scrape.mock_calls
        exp_calls = [
            call("4", mock_start, mock_end),
            call("5", mock_start, mock_end),
            call("6", mock_start, mock_end),
        ]
        self.assertEqual(scrape_calls, exp_calls)

        # And that the raw data fields are set accordingly
        self.assertEqual(dev1.raw_data, None)
        self.assertEqual(dev2.raw_data, None)
        self.assertEqual(dev3.raw_data, None)


class TestProcess(unittest.TestCase):
    # The cli.process(manufacturer) function iterates through the given
    # manufacturer's devices and:
    # - parses raw JSON data into CSV format
    # - runs QA validation on the CSV data
    # - handles and logs all errors appropriately

    def test_all_success(self):
        # Test success on all devices
        mock_parse = Mock(
            side_effect=[
                [["a", "b", "c"], [1, 2, 3], [4, 5, 6], [7, 8, 9]],
                [["foo", "bar", "car"], [4, 2, 3], [4, 1, 2]],
                [["no2", "co2", "co"], [12, 14, 16]],
            ]
        )
        mock_validate = Mock(
            side_effect=[
                ([["a", "b"], [1, 2], [4, 5], [7, 8]], ""),
                ([["foo", "bar"], [4, 2], [4, 1]], ""),
                ([["no2", "co2"], [12, 14]], ""),
            ]
        )
        man = Mock(
            measurands=[{"id": 5, "webid": 8}],
            parse_to_csv=mock_parse,
            validate_data=mock_validate,
        )
        dev1 = Device("1", "4", "foo")
        dev1.raw_data = [1, 2, 3]
        dev2 = Device("2", "5", "foo")
        dev2.raw_data = [8, 10]
        dev3 = Device("3", "6", "foo")
        dev3.raw_data = ["foo", "bar"]
        man.devices = [dev1, dev2, dev3]

        with self.assertLogs(level="INFO") as cm:
            cli.process(man)

        # Assert log is called with expected messages
        self.assertEqual(
            cm.output,
            [
                "INFO:root:Parse into CSV successful for device 1.",
                "INFO:root:Parse into CSV successful for device 2.",
                "INFO:root:Parse into CSV successful for device 3.",
            ],
        )

        # Assert parse_to_csv calls are as expected
        parse_calls = mock_parse.mock_calls
        exp_calls = [call([1, 2, 3]), call([8, 10]), call(["foo", "bar"])]
        self.assertEqual(parse_calls, exp_calls)

        # Assert validate_data calls are as expected
        validate_calls = mock_validate.mock_calls
        exp_calls = [
            call([["a", "b", "c"], [1, 2, 3], [4, 5, 6], [7, 8, 9]]),
            call([["foo", "bar", "car"], [4, 2, 3], [4, 1, 2]]),
            call([["no2", "co2", "co"], [12, 14, 16]]),
        ]
        self.assertEqual(validate_calls, exp_calls)

        # And that the clean data fields are set accordingly
        self.assertEqual(dev1.clean_data, [["a", "b"], [1, 2], [4, 5], [7, 8]])
        self.assertEqual(dev2.clean_data, [["foo", "bar"], [4, 2], [4, 1]])
        self.assertEqual(dev3.clean_data, [["no2", "co2"], [12, 14]])

    def test_no_raw_data(self):
        # Device 3 has no raw data
        mock_parse = Mock(
            side_effect=[
                [["a", "b", "c"], [1, 2, 3], [4, 5, 6], [7, 8, 9]],
                [["no2", "co2", "co"], [12, 14, 16]],
            ]
        )
        mock_validate = Mock(
            side_effect=[
                ([["a", "b"], [1, 2], [4, 5], [7, 8]], ""),
                ([["no2", "co2"], [12, 14]], ""),
            ]
        )

        man = Mock(
            measurands=[{"id": 5, "webid": 8}],
            parse_to_csv=mock_parse,
            validate_data=mock_validate,
        )
        dev1 = Device("1", "4", "foo")
        dev1.raw_data = [1, 2, 3]
        dev2 = Device("2", "5", "foo")
        dev2.raw_data = [8, 10]
        dev3 = Device("3", "6", "foo")
        dev3.raw_data = None
        man.devices = [dev1, dev2, dev3]

        with self.assertLogs(level="INFO") as cm:
            cli.process(man)

        # Assert parse_to_csv calls are as expected
        parse_calls = mock_parse.mock_calls
        exp_calls = [call([1, 2, 3]), call([8, 10])]
        self.assertEqual(parse_calls, exp_calls)

        # Assert validate_data calls are as expected
        validate_calls = mock_validate.mock_calls
        exp_calls = [
            call([["a", "b", "c"], [1, 2, 3], [4, 5, 6], [7, 8, 9]]),
            call([["no2", "co2", "co"], [12, 14, 16]]),
        ]
        self.assertEqual(validate_calls, exp_calls)

        # And that the clean data fields are set accordingly
        self.assertEqual(dev1.clean_data, [["a", "b"], [1, 2], [4, 5], [7, 8]])
        self.assertEqual(dev2.clean_data, [["no2", "co2"], [12, 14]])
        self.assertEqual(dev3.clean_data, None)

    def test_parse_failure(self):
        # Device 2 fails in parsing to CSV
        mock_parse = Mock(
            side_effect=[
                [["a", "b", "c"], [1, 2, 3], [4, 5, 6], [7, 8, 9]],
                utils.DataParseError("bar"),
                [["no2", "co2", "co"], [12, 14, 16]],
            ]
        )
        mock_validate = Mock(
            side_effect=[
                ([["a", "b"], [1, 2], [4, 5], [7, 8]], ""),
                ([["no2", "co2"], [12, 14]], ""),
            ]
        )

        man = Mock(
            measurands=[{"id": 5, "webid": 8}],
            parse_to_csv=mock_parse,
            validate_data=mock_validate,
        )
        dev1 = Device("1", "4", "foo")
        dev1.raw_data = [1, 2, 3]
        dev2 = Device("2", "5", "foo")
        dev2.raw_data = [8, 10]
        dev3 = Device("3", "6", "foo")
        dev3.raw_data = ["foo", "bar"]
        man.devices = [dev1, dev2, dev3]

        with self.assertLogs(level="INFO") as cm:
            cli.process(man)

        # Assert log is called with expected error messages
        # Not going to try and assert equality on the full log as it contains a
        # stack-trace
        self.assertIn(
            "ERROR:root:Unable to parse data into CSV for device 2: bar", cm.output
        )

        # Assert parse_to_csv calls are as expected
        parse_calls = mock_parse.mock_calls
        exp_calls = [call([1, 2, 3]), call([8, 10]), call(["foo", "bar"])]
        self.assertEqual(parse_calls, exp_calls)

        # Assert validate_data calls are as expected
        validate_calls = mock_validate.mock_calls
        exp_calls = [
            call([["a", "b", "c"], [1, 2, 3], [4, 5, 6], [7, 8, 9]]),
            call([["no2", "co2", "co"], [12, 14, 16]]),
        ]
        self.assertEqual(validate_calls, exp_calls)

        # And that the clean data fields are set accordingly
        self.assertEqual(dev1.clean_data, [["a", "b"], [1, 2], [4, 5], [7, 8]])
        self.assertEqual(dev2.clean_data, None)
        self.assertEqual(dev3.clean_data, [["no2", "co2"], [12, 14]])

    def test_no_rows(self):
        # Device 2 parses to CSV, but has no rows of data
        mock_parse = Mock(
            side_effect=[
                [["a", "b", "c"], [1, 2, 3], [4, 5, 6], [7, 8, 9]],
                [],
                [["no2", "co2", "co"], [12, 14, 16]],
            ]
        )
        mock_validate = Mock(
            side_effect=[
                ([["a", "b"], [1, 2], [4, 5], [7, 8]], ""),
                ([["no2", "co2"], [12, 14]], ""),
            ]
        )

        man = Mock(
            measurands=[{"id": 5, "webid": 8}],
            parse_to_csv=mock_parse,
            validate_data=mock_validate,
        )
        dev1 = Device("1", "4", "foo")
        dev1.raw_data = [1, 2, 3]
        dev2 = Device("2", "5", "foo")
        dev2.raw_data = [8, 10]
        dev3 = Device("3", "6", "foo")
        dev3.raw_data = ["foo", "bar"]
        man.devices = [dev1, dev2, dev3]

        with self.assertLogs(level="INFO") as cm:
            cli.process(man)

        # Assert log is called with expected error messages
        # Not going to try and assert equality on the full log as it contains a
        # stack-trace
        self.assertIn(
            "ERROR:root:No time-points have been found in the parsed CSV for device 2.",
            cm.output,
        )

        # Assert parse_to_csv calls are as expected
        parse_calls = mock_parse.mock_calls
        exp_calls = [call([1, 2, 3]), call([8, 10]), call(["foo", "bar"])]
        self.assertEqual(parse_calls, exp_calls)

        # Assert validate_data calls are as expected
        validate_calls = mock_validate.mock_calls
        exp_calls = [
            call([["a", "b", "c"], [1, 2, 3], [4, 5, 6], [7, 8, 9]]),
            call([["no2", "co2", "co"], [12, 14, 16]]),
        ]
        self.assertEqual(validate_calls, exp_calls)

        self.assertEqual(dev1.clean_data, [["a", "b"], [1, 2], [4, 5], [7, 8]])
        self.assertEqual(dev2.clean_data, None)
        self.assertEqual(dev3.clean_data, [["no2", "co2"], [12, 14]])

    def test_validate_failure(self):
        # Device 1 fails in validation call
        mock_parse = Mock(
            side_effect=[
                [["a", "b", "c"], [1, 2, 3], [4, 5, 6], [7, 8, 9]],
                [["foo", "bar", "car"], [4, 2, 3], [4, 1, 2]],
                [["no2", "co2", "co"], [12, 14, 16]],
            ]
        )
        mock_validate = Mock(
            side_effect=[
                utils.ValidateDataError("foo"),
                ([["foo", "bar"], [4, 2], [4, 1]], ""),
                ([["no2", "co2"], [12, 14]], ""),
            ]
        )

        man = Mock(
            measurands=[{"id": 5, "webid": 8}],
            parse_to_csv=mock_parse,
            validate_data=mock_validate,
        )
        dev1 = Device("1", "4", "foo")
        dev1.raw_data = [1, 2, 3]
        dev2 = Device("2", "5", "foo")
        dev2.raw_data = [8, 10]
        dev3 = Device("3", "6", "foo")
        dev3.raw_data = ["foo", "bar"]
        man.devices = [dev1, dev2, dev3]

        with self.assertLogs(level="INFO") as cm:
            cli.process(man)

        # Assert log is called with expected error messages
        # Not going to try and assert equality on the full log as it contains a
        # stack-trace
        self.assertIn("ERROR:root:Data validation error for device 1: foo", cm.output)

        # Assert parse_to_csv calls are as expected
        parse_calls = mock_parse.mock_calls
        exp_calls = [call([1, 2, 3]), call([8, 10]), call(["foo", "bar"])]
        self.assertEqual(parse_calls, exp_calls)

        # Assert validate_data calls are as expected
        validate_calls = mock_validate.mock_calls
        exp_calls = [
            call([["a", "b", "c"], [1, 2, 3], [4, 5, 6], [7, 8, 9]]),
            call([["foo", "bar", "car"], [4, 2, 3], [4, 1, 2]]),
            call([["no2", "co2", "co"], [12, 14, 16]]),
        ]
        self.assertEqual(validate_calls, exp_calls)

        # And that the clean data fields are set accordingly
        self.assertEqual(dev1.clean_data, None)
        self.assertEqual(dev2.clean_data, [["foo", "bar"], [4, 2], [4, 1]])
        self.assertEqual(dev3.clean_data, [["no2", "co2"], [12, 14]])


class TestSummariseRun(unittest.TestCase):

    # utils.tabular_summary has limited error handling, as most of the input data
    # is automatically generated with default values (i.e. the number of clean
    # measurands which default to 0).
    # The 2 pieces that derive from user input are the device locations and
    # expected recording frequencies. Error handling for these values is
    # provided.
    # Basic error handling covers the remaining potential sources of error, such
    # as if timestamps or any measurands are missing, although there aren't any
    # further checks on the values themselves.
    # I.e. not testing that all counts are valid positive ints, and no
    # measurand has more clean values than available timestamps.

    # Mention that measurands based on first device

    def test_success(self):
        summaries = [
            {
                "manufacturer": "foo",
                "frequency": 5,
                "devices": {
                    "dev1": {"co2": 5, "no": 0, "timestamp": 10, "Location": "York"},
                    "dev2": {"co2": 5, "no": 1, "timestamp": 10, "Location": "Sweden"},
                },
            },
            {
                "manufacturer": "bar",
                "frequency": 60,
                "devices": {
                    "manu2dev1": {
                        "o3": 1,
                        "no": 0,
                        "timestamp": 1,
                        "Location": "Honolulu",
                    },
                    "manu2dev2": {"o3": 0, "no": 0, "timestamp": 0, "Location": "NYC"},
                },
            },
        ]
        exp = {
            "foo": [
                ["Device ID", "Location", "Timestamps", "co2", "no"],
                ["dev1", "York", "10 (8%)", "5 (4%)", "0 (0%)"],
                ["dev2", "Sweden", "10 (8%)", "5 (4%)", "1 (1%)"],
            ],
            "bar": [
                ["Device ID", "Location", "Timestamps", "no", "o3"],
                ["manu2dev1", "Honolulu", "1 (0%)", "0 (0%)", "1 (0%)"],
                ["manu2dev2", "NYC", "0 (0%)", "0 (0%)", "0 (0%)"],
            ],
        }
        res = cli.tabular_summary(summaries)
        self.assertEqual(res, exp)

    def test_success2(self):
        # Test with more clean data
        summaries = [
            {
                "manufacturer": "foo",
                "frequency": 4,
                "devices": {
                    "dev1": {"co2": 48, "no": 32, "timestamp": 96, "Location": "York"},
                    "dev2": {
                        "co2": 68,
                        "no": 42,
                        "timestamp": 82,
                        "Location": "Sweden",
                    },
                },
            },
            {
                "manufacturer": "bar",
                "frequency": 60,
                "devices": {
                    "manu2dev1": {
                        "o3": 766,
                        "no": 1358,
                        "timestamp": 1358,
                        "Location": "Honolulu",
                    },
                    "manu2dev2": {
                        "o3": 323,
                        "no": 232,
                        "timestamp": 829,
                        "Location": "NYC",
                    },
                },
            },
        ]
        exp = {
            "foo": [
                ["Device ID", "Location", "Timestamps", "co2", "no"],
                ["dev1", "York", "96 (100%)", "48 (50%)", "32 (33%)"],
                ["dev2", "Sweden", "82 (85%)", "68 (71%)", "42 (44%)"],
            ],
            "bar": [
                ["Device ID", "Location", "Timestamps", "no", "o3"],
                ["manu2dev1", "Honolulu", "1358 (94%)", "1358 (94%)", "766 (53%)"],
                ["manu2dev2", "NYC", "829 (58%)", "232 (16%)", "323 (22%)"],
            ],
        }
        res = cli.tabular_summary(summaries)
        self.assertEqual(res, exp)

    def test_no_frequency(self):
        # No manufacturer frequency in input dict.
        # Should display available timestamps without % of expected
        summaries = [
            {
                "manufacturer": "foo",
                "devices": {
                    "dev1": {"co2": 5, "no": 0, "timestamp": 10, "Location": "York"},
                    "dev2": {"co2": 5, "no": 1, "timestamp": 10, "Location": "Sweden"},
                },
            },
            {
                "manufacturer": "bar",
                "frequency": 60,
                "devices": {
                    "manu2dev1": {
                        "o3": 1,
                        "no": 0,
                        "timestamp": 1,
                        "Location": "Honolulu",
                    },
                    "manu2dev2": {"o3": 0, "no": 0, "timestamp": 0, "Location": "NYC"},
                },
            },
        ]
        exp = {
            "foo": [
                ["Device ID", "Location", "Timestamps", "co2", "no"],
                ["dev1", "York", "10", "5", "0"],
                ["dev2", "Sweden", "10", "5", "1"],
            ],
            "bar": [
                ["Device ID", "Location", "Timestamps", "no", "o3"],
                ["manu2dev1", "Honolulu", "1 (0%)", "0 (0%)", "1 (0%)"],
                ["manu2dev2", "NYC", "0 (0%)", "0 (0%)", "0 (0%)"],
            ],
        }
        res = cli.tabular_summary(summaries)
        self.assertEqual(res, exp)

    def test_no_location(self):
        # When location isn't available should just have empty column
        summaries = [
            {
                "manufacturer": "foo",
                "frequency": 4,
                "devices": {
                    "dev1": {"co2": 48, "no": 32, "timestamp": 96},
                    "dev2": {"co2": 68, "no": 42, "timestamp": 82},
                },
            },
            {
                "manufacturer": "bar",
                "frequency": 60,
                "devices": {
                    "manu2dev1": {
                        "o3": 766,
                        "no": 1358,
                        "timestamp": 1358,
                        "Location": "Honolulu",
                    },
                    "manu2dev2": {
                        "o3": 323,
                        "no": 232,
                        "timestamp": 829,
                        "Location": "NYC",
                    },
                },
            },
        ]
        exp = {
            "foo": [
                ["Device ID", "Location", "Timestamps", "co2", "no"],
                ["dev1", "", "96 (100%)", "48 (50%)", "32 (33%)"],
                ["dev2", "", "82 (85%)", "68 (71%)", "42 (44%)"],
            ],
            "bar": [
                ["Device ID", "Location", "Timestamps", "no", "o3"],
                ["manu2dev1", "Honolulu", "1358 (94%)", "1358 (94%)", "766 (53%)"],
                ["manu2dev2", "NYC", "829 (58%)", "232 (16%)", "323 (22%)"],
            ],
        }
        res = cli.tabular_summary(summaries)
        self.assertEqual(res, exp)

    def test_no_measurands(self):
        # When measurands aren't available in dict then should just have empty
        # columns
        summaries = [
            {
                "manufacturer": "foo",
                "frequency": 4,
                "devices": {
                    "dev1": {"co2": 48, "no": 32, "timestamp": 96, "Location": "York"},
                    "dev2": {"no": 42, "timestamp": 82, "Location": "Sweden",},
                },
            },
            {
                "manufacturer": "bar",
                "frequency": 60,
                "devices": {
                    "manu2dev1": {
                        "no": 1358,
                        "timestamp": 1358,
                        "Location": "Honolulu",
                    },
                    "manu2dev2": {"o3": 323, "timestamp": 829, "Location": "NYC",},
                },
            },
        ]
        exp = {
            "foo": [
                ["Device ID", "Location", "Timestamps", "co2", "no"],
                ["dev1", "York", "96 (100%)", "48 (50%)", "32 (33%)"],
                ["dev2", "Sweden", "82 (85%)", "", "42 (44%)"],
            ],
            "bar": [
                ["Device ID", "Location", "Timestamps", "no", "o3"],
                ["manu2dev1", "Honolulu", "1358 (94%)", "1358 (94%)", ""],
                ["manu2dev2", "NYC", "829 (58%)", "", "323 (22%)"],
            ],
        }
        res = cli.tabular_summary(summaries)
        self.assertEqual(res, exp)

    def test_no_timestamp(self):
        # Likewise no timestamp available should make the associated column
        # empty and remove the %s from other measurands
        summaries = [
            {
                "manufacturer": "foo",
                "frequency": 4,
                "devices": {
                    "dev1": {"co2": 48, "no": 32, "Location": "York"},
                    "dev2": {
                        "co2": 68,
                        "no": 42,
                        "timestamp": 82,
                        "Location": "Sweden",
                    },
                },
            },
            {
                "manufacturer": "bar",
                "frequency": 60,
                "devices": {
                    "manu2dev1": {
                        "o3": 766,
                        "no": 1358,
                        "timestamp": 1358,
                        "Location": "Honolulu",
                    },
                    "manu2dev2": {
                        "o3": 323,
                        "no": 232,
                        "timestamp": 829,
                        "Location": "NYC",
                    },
                },
            },
        ]
        exp = {
            "foo": [
                ["Device ID", "Location", "Timestamps", "co2", "no"],
                ["dev1", "York", "", "48 (50%)", "32 (33%)"],
                ["dev2", "Sweden", "82 (85%)", "68 (71%)", "42 (44%)"],
            ],
            "bar": [
                ["Device ID", "Location", "Timestamps", "no", "o3"],
                ["manu2dev1", "Honolulu", "1358 (94%)", "1358 (94%)", "766 (53%)"],
                ["manu2dev2", "NYC", "829 (58%)", "232 (16%)", "323 (22%)"],
            ],
        }
        res = cli.tabular_summary(summaries)
        self.assertEqual(res, exp)


class TestUploadDataGoogleDrive(unittest.TestCase):
    # the cli.upload_data_googledrive function uploads a list of files
    # with the same mime_type to Google Drive

    def test_success(self):
        with patch("quantscraper.cli.utils.upload_file_google_drive") as mock_upload:
            mock_service = Mock()
            fns = ["1.txt", "2.txt", "3.txt"]
            folder_id = "FoOBaR"
            mime_type = "text/foobar"
            exp_calls = [call(mock_service, fn, folder_id, mime_type) for fn in fns]

            cli.upload_data_googledrive(mock_service, fns, folder_id, mime_type)

            calls = mock_upload.mock_calls

            self.assertEqual(calls, exp_calls)

    def test_empty_list(self):
        with patch("quantscraper.cli.utils.upload_file_google_drive") as mock_upload:
            mock_service = Mock()
            fns = []
            folder_id = "FoOBaR"
            mime_type = "text/foobar"
            exp_calls = []

            cli.upload_data_googledrive(mock_service, fns, folder_id, mime_type)

            calls = mock_upload.mock_calls

            self.assertEqual(calls, exp_calls)

    def test_fns_None(self):
        with patch("quantscraper.cli.utils.upload_file_google_drive") as mock_upload:
            mock_service = Mock()
            fns = None
            folder_id = "FoOBaR"
            mime_type = "text/foobar"
            exp_calls = []

            cli.upload_data_googledrive(mock_service, fns, folder_id, mime_type)

            calls = mock_upload.mock_calls

            self.assertEqual(calls, exp_calls)


class TestSaveCleanData(unittest.TestCase):
    # Tests cli.save_data, which iterates through all devices and extracts
    # their data to be saved. This class tests being passed clean data.
    cfg = defaultdict(str)
    fields = []
    aeroqual = Aeroqual.Aeroqual(cfg, fields)

    def test_success(self):
        self.aeroqual._devices = []
        dev1 = Device(id="1", webid="1", location="foo")
        dev1.clean_data = [[1, 2, 3], [4, 5, 6]]
        dev2 = Device(id="2", webid="2", location="bar")
        dev2.clean_data = [[7, 8, 9]]
        self.aeroqual.add_device(dev1)
        self.aeroqual.add_device(dev2)

        # Need to patch os.path to force directory to exist
        with patch("quantscraper.cli.os.path.isdir") as mock_isdir:
            mock_isdir.return_value = True

            # patch actual function that saves
            with patch("quantscraper.utils.save_csv_file") as mock_save:

                try:
                    res = cli.save_data(self.aeroqual, "dummyFolder", "foobar", "clean")

                    calls = mock_save.mock_calls
                    exp_calls = [
                        call(
                            [[1, 2, 3], [4, 5, 6]], "dummyFolder/Aeroqual_1_foobar.csv",
                        ),
                        call([[7, 8, 9]], "dummyFolder/Aeroqual_2_foobar.csv"),
                    ]
                    self.assertEqual(calls, exp_calls)
                    # Function should output names of files that are
                    # successfully saved
                    self.assertEqual(
                        res,
                        [
                            "dummyFolder/Aeroqual_1_foobar.csv",
                            "dummyFolder/Aeroqual_2_foobar.csv",
                        ],
                    )
                except:
                    self.fail("Test raised error when should have passed.")

    def test_dir_doesnt_exist(self):
        self.aeroqual._devices = []
        dev1 = Device(id="1", webid="1", location="foo")
        dev1.clean_data = [[1, 2, 3], [4, 5, 6]]
        dev2 = Device(id="2", webid="2", location="bar")
        dev2.clean_data = [[7, 8, 9]]
        self.aeroqual.add_device(dev1)
        self.aeroqual.add_device(dev2)

        # Need to patch os.path to force directory to not exist
        with patch("quantscraper.cli.os.path.isdir") as mock_isdir:
            mock_isdir.return_value = False

            with patch("quantscraper.utils.save_csv_file") as mock_save:

                with self.assertRaises(utils.DataSavingError):
                    cli.save_data(self.aeroqual, "dummyFolder", "startT", "clean")

    def test_success_None_data(self):
        # in case a dataset for a device is None, then shouldn't attempt to save
        self.aeroqual._devices = []
        dev1 = Device(id="1", webid="1", location="foo")
        dev1.clean_data = [[1, 2, 3], [4, 5, 6]]
        dev2 = Device(id="2", webid="2", location="bar")
        dev2.clean_data = None
        self.aeroqual.add_device(dev1)
        self.aeroqual.add_device(dev2)

        # Need to patch os.path to force directory to exist
        with patch("quantscraper.cli.os.path.isdir") as mock_isdir:
            mock_isdir.return_value = True

            # patch actual function that saves
            with patch("quantscraper.utils.save_csv_file") as mock_save:

                try:
                    res = cli.save_data(self.aeroqual, "dummyFolder", "today", "clean")

                    # This inner function should only be called once on account
                    # of second device not having data
                    mock_save.assert_called_once_with(
                        [[1, 2, 3], [4, 5, 6]], "dummyFolder/Aeroqual_1_today.csv"
                    )
                    # Function should only return filename from first file that
                    # saved successfully
                    self.assertEqual(res, ["dummyFolder/Aeroqual_1_today.csv"])
                except:
                    self.fail("Test raised error when should have passed.")

    def test_error_saving_file(self):
        # in case a file already exists then shouldn't save
        self.aeroqual._devices = []
        dev1 = Device(id="1", webid="1", location="foo")
        dev1.clean_data = [[1, 2, 3], [4, 5, 6]]
        dev2 = Device(id="2", webid="2", location="bar")
        dev2.clean_data = [[7, 8, 9]]
        self.aeroqual.add_device(dev1)
        self.aeroqual.add_device(dev2)

        # Need to patch os.path to force directory to exist
        with patch("quantscraper.cli.os.path.isdir") as mock_isdir:
            mock_isdir.return_value = True

            # patch actual function that saves
            with patch("quantscraper.utils.save_csv_file") as mock_save:
                mock_save.side_effect = ["", utils.DataSavingError("")]

                try:
                    res = cli.save_data(self.aeroqual, "dummyFolder", "foobar", "clean")

                    calls = mock_save.mock_calls
                    exp_calls = [
                        call(
                            [[1, 2, 3], [4, 5, 6]], "dummyFolder/Aeroqual_1_foobar.csv",
                        ),
                        call([[7, 8, 9]], "dummyFolder/Aeroqual_2_foobar.csv"),
                    ]
                    self.assertEqual(calls, exp_calls)
                    # Should only have first filename returned
                    self.assertEqual(res, ["dummyFolder/Aeroqual_1_foobar.csv"])
                except:
                    self.fail("Test raised error when should have passed.")


class TestSaveRawData(unittest.TestCase):
    # Tests cli.save_data, which iterates through all devices and extracts
    # their data to be saved. This class tests being passed raw data.

    cfg = defaultdict(str)
    fields = []
    aeroqual = Aeroqual.Aeroqual(cfg, fields)

    def test_success(self):
        # Set dummy data
        self.aeroqual._devices = []
        dev1 = Device(id="1", webid="1", location="foo")
        dev1.raw_data = [[1, 2, 3], [4, 5, 6]]
        dev2 = Device(id="2", webid="2", location="bar")
        dev2.raw_data = [[7, 8, 9]]
        self.aeroqual.add_device(dev1)
        self.aeroqual.add_device(dev2)

        # Need to patch os.path to force directory to exist
        with patch("quantscraper.utils.os.path.isdir") as mock_isdir:
            mock_isdir.return_value = True

            # patch actual function that saves
            with patch("quantscraper.utils.save_json_file") as mock_save:

                try:
                    res = cli.save_data(self.aeroqual, "dummyFolder", "day", "raw")

                    calls = mock_save.mock_calls
                    exp_calls = [
                        call(
                            [[1, 2, 3], [4, 5, 6]], "dummyFolder/Aeroqual_1_day.json",
                        ),
                        call([[7, 8, 9]], "dummyFolder/Aeroqual_2_day.json"),
                    ]
                    self.assertEqual(calls, exp_calls)
                    # should return both filenames as saved successfully
                    self.assertEqual(
                        res,
                        [
                            "dummyFolder/Aeroqual_1_day.json",
                            "dummyFolder/Aeroqual_2_day.json",
                        ],
                    )
                except:
                    self.fail("Test raised error when should have passed.")

    def test_dir_doesnt_exist(self):
        # Set dummy data
        self.aeroqual._devices = []
        dev1 = Device(id="1", webid="1", location="foo")
        dev1.raw_data = [[1, 2, 3], [4, 5, 6]]
        dev2 = Device(id="2", webid="2", location="bar")
        dev2.raw_data = [[7, 8, 9]]
        self.aeroqual.add_device(dev1)
        self.aeroqual.add_device(dev2)

        # Need to patch os.path to force directory to not exist
        with patch("quantscraper.cli.os.path.isdir") as mock_isdir:
            mock_isdir.return_value = False

            with patch("quantscraper.utils.save_json_file"):

                with self.assertRaises(utils.DataSavingError):
                    cli.save_data(self.aeroqual, "dummyFolder", "foobar", "raw")

    def test_success_None_data(self):
        # Set dummy data
        self.aeroqual._devices = []
        dev1 = Device(id="1", webid="1", location="foo")
        dev1._raw_data = [[1, 2, 3], [4, 5, 6]]
        dev2 = Device(id="2", webid="2", location="bar")
        dev2._raw_data = None
        self.aeroqual.add_device(dev1)
        self.aeroqual.add_device(dev2)

        # Need to patch os.path to force directory to exist
        with patch("quantscraper.cli.os.path.isdir") as mock_isdir:
            mock_isdir.return_value = True

            # patch actual function that saves
            with patch("quantscraper.utils.save_json_file") as mock_save:

                try:
                    res = cli.save_data(self.aeroqual, "dummyFolder", "day", "raw")

                    # This inner function should only be called once on account
                    # of second device not having data
                    mock_save.assert_called_once_with(
                        [[1, 2, 3], [4, 5, 6]], "dummyFolder/Aeroqual_1_day.json",
                    )
                    # should return both filenames as saved successfully
                    self.assertEqual(res, ["dummyFolder/Aeroqual_1_day.json"])
                except:
                    self.fail("Test raised error when should have passed.")

    def test_error_saving_file(self):
        # First file saves successfully but second fails as that filename
        # already exists
        # Set dummy data
        self.aeroqual._devices = []
        dev1 = Device(id="1", webid="1", location="foo")
        dev1.raw_data = [[1, 2, 3], [4, 5, 6]]
        dev2 = Device(id="2", webid="2", location="bar")
        dev2.raw_data = [[7, 8, 9]]
        self.aeroqual.add_device(dev1)
        self.aeroqual.add_device(dev2)

        # Need to patch os.path to force directory to exist
        with patch("quantscraper.cli.os.path.isdir") as mock_isdir:
            mock_isdir.return_value = True

            # patch actual function that saves
            with patch("quantscraper.utils.save_json_file") as mock_save:
                mock_save.side_effect = ["", utils.DataSavingError("")]

                try:
                    res = cli.save_data(self.aeroqual, "dummyFolder", "foobar", "raw")

                    calls = mock_save.mock_calls
                    exp_calls = [
                        call(
                            [[1, 2, 3], [4, 5, 6]],
                            "dummyFolder/Aeroqual_1_foobar.json",
                        ),
                        call([[7, 8, 9]], "dummyFolder/Aeroqual_2_foobar.json"),
                    ]
                    self.assertEqual(calls, exp_calls)
                    # Should only have first filename returned
                    self.assertEqual(res, ["dummyFolder/Aeroqual_1_foobar.json"])
                except:
                    self.fail("Test raised error when should have passed.")
