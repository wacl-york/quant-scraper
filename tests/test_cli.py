"""
    test_cli.py
    ~~~~~~~~~~~

    Unit tests for cli functions.
"""

import datetime
import unittest
import configparser
import logging
from unittest.mock import patch, MagicMock, Mock, call

import quantscraper.cli as cli
import quantscraper.utils as utils


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
            mock_addargument.assert_called_once_with(
                "configfilepath",
                metavar="FILE",
                help="Location of INI configuration file",
            )
            mock_parseargs.assert_called_once_with()


class TestSetupConfig(unittest.TestCase):

    # Ensures the expected calls are made
    def test_success(self):
        with patch("quantscraper.cli.configparser") as mock_cp:
            mock_read = Mock()
            mock_sections = Mock(return_value=[1, 2, 3])

            mock_cfginstance = Mock(sections=mock_sections, read=mock_read)
            mock_ConfigParser = Mock(return_value=mock_cfginstance)
            mock_cp.ConfigParser = mock_ConfigParser

            res = cli.setup_config("foo.ini")

            self.assertEqual(res, mock_cfginstance)
            mock_read.assert_called_once_with("foo.ini")

    def test_errorraised_no_sections(self):
        with patch("quantscraper.cli.configparser") as mock_cp:
            mock_read = Mock()
            mock_sections = Mock(return_value=[])

            mock_cfginstance = Mock(sections=mock_sections, read=mock_read)
            mock_ConfigParser = Mock(return_value=mock_cfginstance)
            mock_cp.ConfigParser = mock_ConfigParser

            with self.assertRaises(utils.SetupError):
                res = cli.setup_config("foo.ini")


class TestSetupScrapingTimeframe(unittest.TestCase):
    def test_no_start_end_times(self):
        # Don't pass in start time or end time, so the output time should be
        # yesterday midnight to 1 second before following midnight

        # Provide config without start or end time specified
        cfg = configparser.ConfigParser()
        cfg.read("example.ini")
        cfg.remove_option("Main", "start_time")
        cfg.remove_option("Main", "end_time")

        # Mock date.today() to a fixed date
        with patch("quantscraper.cli.date", autospec=True) as mock_date:
            mock_today = Mock(return_value=datetime.date(2012, 3, 17))
            mock_date.today = mock_today

            cli.setup_scraping_timeframe(cfg)

            # assert cfg times are as expected, as this function modifies cfg by
            # reference rather than returning it directly
            self.assertEqual(cfg.get("Main", "start_time"), "2012-03-16T00:00:00")
            self.assertEqual(cfg.get("Main", "end_time"), "2012-03-16T23:59:59.999999")

    def test_no_end_time(self):
        # Don't pass in end time, so the output time should be
        # specified time to 1 second before today's midnight

        # Provide config without start or end time specified
        cfg = configparser.ConfigParser()
        cfg.read("example.ini")
        cfg.set("Main", "start_time", "2012-02-28T13:59:00")
        cfg.remove_option("Main", "end_time")

        # Mock date.today() to a fixed date
        with patch("quantscraper.cli.date", autospec=True) as mock_date:
            mock_today = Mock(return_value=datetime.date(2012, 3, 16))
            mock_date.today = mock_today

            cli.setup_scraping_timeframe(cfg)

            # assert cfg times are as expected, as this function modifies cfg by
            # reference rather than returning it directly
            self.assertEqual(cfg.get("Main", "start_time"), "2012-02-28T13:59:00")
            self.assertEqual(cfg.get("Main", "end_time"), "2012-03-15T23:59:59.999999")

    def test_no_start_time(self):
        # Don't pass in start time, so the output time should be
        # yesterday's midnight to specified end time

        # Provide config without start or end time specified
        cfg = configparser.ConfigParser()
        cfg.read("example.ini")
        cfg.remove_option("Main", "start_time")
        cfg.set("Main", "end_time", "2035-10-12T14:22:00")

        # Mock date.today() to a fixed date
        with patch("quantscraper.cli.date", autospec=True) as mock_date:
            mock_today = Mock(return_value=datetime.date(2035, 10, 12))
            mock_date.today = mock_today

            cli.setup_scraping_timeframe(cfg)

            # assert cfg times are as expected, as this function modifies cfg by
            # reference rather than returning it directly
            self.assertEqual(cfg.get("Main", "start_time"), "2035-10-11T00:00:00")
            self.assertEqual(cfg.get("Main", "end_time"), "2035-10-12T14:22:00")

    def test_both_times_specified(self):
        # Both start and end times are specified in config file

        # Provide config without start or end time specified
        cfg = configparser.ConfigParser()
        cfg.read("example.ini")
        cfg.set("Main", "start_time", "2035-10-11T12:00:00")
        cfg.set("Main", "end_time", "2035-10-12T14:22:00")

        # Mock date.today() to a fixed date
        with patch("quantscraper.cli.date", autospec=True) as mock_date:
            mock_today = Mock(return_value=datetime.date(2035, 10, 12))
            mock_date.today = mock_today

            cli.setup_scraping_timeframe(cfg)

            # assert cfg times are as expected, as this function modifies cfg by
            # reference rather than returning it directly
            self.assertEqual(cfg.get("Main", "start_time"), "2035-10-11T12:00:00")
            self.assertEqual(cfg.get("Main", "end_time"), "2035-10-12T14:22:00")

    def test_start_later_end_both_passed_in(self):
        # Here start date is later than end. Shouldn't be allowed!
        # Here both are passed in
        cfg = configparser.ConfigParser()
        cfg.read("example.ini")
        cfg.set("Main", "start_time", "2035-10-13T12:00:00")
        cfg.set("Main", "end_time", "2035-10-12T14:22:00")

        # Mock date.today() to a fixed date
        with patch("quantscraper.cli.date", autospec=True) as mock_date:
            mock_today = Mock(return_value=datetime.date(2035, 10, 12))
            mock_date.today = mock_today

            with self.assertRaises(utils.TimeError):
                cli.setup_scraping_timeframe(cfg)

    def test_start_later_end_start_assumed(self):
        # Here start date is later than end. Shouldn't be allowed!
        # Here just the end date is passed in and start date is taken as default
        cfg = configparser.ConfigParser()
        cfg.read("example.ini")
        cfg.remove_option("Main", "start_time")
        cfg.set("Main", "end_time", "2019-08-15T23:59:59")

        # Mock date.today() to a fixed date
        with patch("quantscraper.cli.date", autospec=True) as mock_date:
            mock_today = Mock(return_value=datetime.date(2019, 8, 17))
            mock_date.today = mock_today

            with self.assertRaises(utils.TimeError):
                cli.setup_scraping_timeframe(cfg)

    def test_start_later_end_end_assumed(self):
        # Here start date is later than end. Shouldn't be allowed!
        # Here just the start date is passed in and end date is taken as default
        cfg = configparser.ConfigParser()
        cfg.read("example.ini")
        cfg.set("Main", "start_time", "2019-08-17T00:00:00")
        cfg.remove_option("Main", "end_time")

        # Mock date.today() to a fixed date
        with patch("quantscraper.cli.date", autospec=True) as mock_date:
            mock_today = Mock(return_value=datetime.date(2019, 8, 17))
            mock_date.today = mock_today

            with self.assertRaises(utils.TimeError):
                cli.setup_scraping_timeframe(cfg)

    def test_start_equal_end_both_passed_in(self):
        # Here start date is equal to end. Shouldn't be allowed!
        # Here both are passed in
        cfg = configparser.ConfigParser()
        cfg.read("example.ini")
        cfg.set("Main", "start_time", "2035-10-13T14:22:13")
        cfg.set("Main", "end_time", "2035-10-13T14:22:13")

        # Mock date.today() to a fixed date
        with patch("quantscraper.cli.date", autospec=True) as mock_date:
            mock_today = Mock(return_value=datetime.date(2035, 10, 12))
            mock_date.today = mock_today

            with self.assertRaises(utils.TimeError):
                cli.setup_scraping_timeframe(cfg)

    def test_start_equal_end_start_assumed(self):
        # Here start date is equal to end. Shouldn't be allowed!
        # Here just the end date is passed in and start date is taken as default
        cfg = configparser.ConfigParser()
        cfg.read("example.ini")
        cfg.remove_option("Main", "start_time")
        cfg.set("Main", "end_time", "2019-08-16T00:00:00")

        # Mock date.today() to a fixed date
        with patch("quantscraper.cli.date", autospec=True) as mock_date:
            mock_today = Mock(return_value=datetime.date(2019, 8, 17))
            mock_date.today = mock_today

            with self.assertRaises(utils.TimeError):
                cli.setup_scraping_timeframe(cfg)

    def test_start_equal_end_end_assumed(self):
        # Here start date is equal to end. Shouldn't be allowed!
        # Here just the start date is passed in and end date is taken as default
        cfg = configparser.ConfigParser()
        cfg.read("example.ini")
        cfg.set("Main", "start_time", "2019-08-16T23:59:59.999999")
        cfg.remove_option("Main", "end_time")

        # Mock date.today() to a fixed date
        with patch("quantscraper.cli.date", autospec=True) as mock_date:
            mock_today = Mock(return_value=datetime.date(2019, 8, 17))
            mock_date.today = mock_today

            with self.assertRaises(utils.TimeError):
                cli.setup_scraping_timeframe(cfg)

    def test_formatting_error_start(self):
        # Pass in a poorly specified time format to start time
        cfg = configparser.ConfigParser()
        cfg.read("example.ini")
        cfg.set("Main", "start_time", "2012/03/04 15:32")

        # Mock date.today() to a fixed date
        with patch("quantscraper.cli.date", autospec=True) as mock_date:
            mock_today = Mock(return_value=datetime.date(2019, 8, 17))
            mock_date.today = mock_today

            with self.assertRaises(utils.TimeError):
                cli.setup_scraping_timeframe(cfg)


class TestScrape(unittest.TestCase):
    # Tests the scrape() function, which iterates through a given manufacturer's
    # devices and scrapes their data

    def test_success_all_ids(self):
        # Test success on all devices
        mock_scrape = Mock(side_effect=["foo", "bar", "cat"])
        man = Mock(
            device_ids=["1", "2", "3"],
            device_web_ids=["4", "5", "6"],
            raw_data={},
            scrape_device=mock_scrape,
        )
        with self.assertLogs(level="INFO") as cm:
            cli.scrape(man)

        # Assert log is called with expected messages
        self.assertEqual(
            cm.output,
            [
                "INFO:root:Attempting to scrape data for device 1...",
                "INFO:root:Scrape successful.",
                "INFO:root:Attempting to scrape data for device 2...",
                "INFO:root:Scrape successful.",
                "INFO:root:Attempting to scrape data for device 3...",
                "INFO:root:Scrape successful.",
            ],
        )

        # Assert scrape calls are as expected
        scrape_calls = mock_scrape.mock_calls
        exp_calls = [call("4"), call("5"), call("6")]
        self.assertEqual(scrape_calls, exp_calls)

        # And that the raw data fields are set accordingly
        self.assertEqual(man.raw_data, {"1": "foo", "2": "bar", "3": "cat"})

    def test_mixed_success(self):
        # 2nd device raises utils.DataDownloadError
        mock_scrape = Mock(side_effect=["foo", utils.DataDownloadError(""), "cat"])
        man = Mock(
            device_ids=["1", "2", "3"],
            device_web_ids=["4", "5", "6"],
            raw_data={},
            scrape_device=mock_scrape,
        )

        with self.assertLogs(level="INFO") as cm:
            cli.scrape(man)

        # Assert log is called with expected messages
        # NB: using assertIn rather than assertEqual as hard to produce the
        # expected stacktrace that will also be logged alongside the error
        # message.
        self.assertIn("INFO:root:Attempting to scrape data for device 1...", cm.output)
        self.assertIn("INFO:root:Scrape successful.", cm.output)
        self.assertIn("INFO:root:Attempting to scrape data for device 2...", cm.output)
        self.assertIn("ERROR:root:Unable to download data for device 2.", cm.output)
        self.assertIn("INFO:root:Attempting to scrape data for device 3...", cm.output)
        self.assertIn("INFO:root:Scrape successful.", cm.output)

        # Assert scrape calls are as expected
        scrape_calls = mock_scrape.mock_calls
        exp_calls = [call("4"), call("5"), call("6")]
        self.assertEqual(scrape_calls, exp_calls)

        # And that the raw data fields are set accordingly
        self.assertEqual(man.raw_data, {"1": "foo", "2": None, "3": "cat"})

    def test_all_failure(self):
        # all devices fail to download data
        mock_scrape = Mock(
            side_effect=[
                utils.DataDownloadError(""),
                utils.DataDownloadError(""),
                utils.DataDownloadError(""),
            ]
        )
        man = Mock(
            device_ids=["1", "2", "3"],
            device_web_ids=["4", "5", "6"],
            raw_data={},
            scrape_device=mock_scrape,
        )

        with self.assertLogs(level="INFO") as cm:
            cli.scrape(man)

        # Assert log is called with expected messages
        # NB: using assertIn rather than assertEqual as hard to produce the
        # expected stacktrace that will also be logged alongside the error
        # message.
        self.assertIn("INFO:root:Attempting to scrape data for device 1...", cm.output)
        self.assertIn("ERROR:root:Unable to download data for device 1.", cm.output)
        self.assertIn("INFO:root:Attempting to scrape data for device 2...", cm.output)
        self.assertIn("ERROR:root:Unable to download data for device 2.", cm.output)
        self.assertIn("INFO:root:Attempting to scrape data for device 3...", cm.output)
        self.assertIn("ERROR:root:Unable to download data for device 3.", cm.output)

        # Assert scrape calls are as expected
        scrape_calls = mock_scrape.mock_calls
        exp_calls = [call("4"), call("5"), call("6")]
        self.assertEqual(scrape_calls, exp_calls)

        # And that the raw data fields are set accordingly
        self.assertEqual(man.raw_data, {"1": None, "2": None, "3": None})


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
                [["a", "b"], [1, 2], [4, 5], [7, 8]],
                [["foo", "bar"], [4, 2], [4, 1]],
                [["no2", "co2"], [12, 14]],
            ]
        )
        man = Mock(
            device_ids=["1", "2", "3"],
            device_web_ids=["4", "5", "6"],
            raw_data={"1": [1, 2, 3], "2": [8, 10], "3": ["foo", "bar"]},
            clean_data={},
            parse_to_csv=mock_parse,
            validate_data=mock_validate,
        )
        with self.assertLogs(level="INFO") as cm:
            cli.process(man)

        # Assert log is called with expected messages
        self.assertEqual(
            cm.output,
            [
                "INFO:root:Cleaning data from device 1...",
                "INFO:root:Attempting to parse data into CSV...",
                "INFO:root:Parse successful. Samples at 3 time-points have been recorded.",
                "INFO:root:Running validation...",
                "INFO:root:Validation successful.",
                "INFO:root:Cleaning data from device 2...",
                "INFO:root:Attempting to parse data into CSV...",
                "INFO:root:Parse successful. Samples at 2 time-points have been recorded.",
                "INFO:root:Running validation...",
                "INFO:root:Validation successful.",
                "INFO:root:Cleaning data from device 3...",
                "INFO:root:Attempting to parse data into CSV...",
                "INFO:root:Parse successful. Samples at 1 time-points have been recorded.",
                "INFO:root:Running validation...",
                "INFO:root:Validation successful.",
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
        self.assertEqual(
            man.clean_data,
            {
                "1": [["a", "b"], [1, 2], [4, 5], [7, 8]],
                "2": [["foo", "bar"], [4, 2], [4, 1]],
                "3": [["no2", "co2"], [12, 14]],
            },
        )

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
                [["a", "b"], [1, 2], [4, 5], [7, 8]],
                [["no2", "co2"], [12, 14]],
            ]
        )

        man = Mock(
            device_ids=["1", "2", "3"],
            device_web_ids=["4", "5", "6"],
            raw_data={"1": [1, 2, 3], "2": [8, 10], "3": None},
            clean_data={},
            parse_to_csv=mock_parse,
            validate_data=mock_validate,
        )
        with self.assertLogs(level="INFO") as cm:
            cli.process(man)

        # Assert log is called with expected error messages
        # Not going to try and assert equality on the full log as it contains a
        # stack-trace
        self.assertIn("WARNING:root:No available raw data.", cm.output)

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
        self.assertEqual(
            man.clean_data,
            {
                "1": [["a", "b"], [1, 2], [4, 5], [7, 8]],
                "2": [["no2", "co2"], [12, 14]],
                "3": None,
            },
        )

    def test_parse_failure(self):
        # Device 2 fails in parsing to CSV
        mock_parse = Mock(
            side_effect=[
                [["a", "b", "c"], [1, 2, 3], [4, 5, 6], [7, 8, 9]],
                utils.DataParseError(""),
                [["no2", "co2", "co"], [12, 14, 16]],
            ]
        )
        mock_validate = Mock(
            side_effect=[
                [["a", "b"], [1, 2], [4, 5], [7, 8]],
                [["no2", "co2"], [12, 14]],
            ]
        )

        man = Mock(
            device_ids=["1", "2", "3"],
            device_web_ids=["4", "5", "6"],
            raw_data={"1": [1, 2, 3], "2": [8, 10], "3": ["foo", "bar"]},
            clean_data={},
            parse_to_csv=mock_parse,
            validate_data=mock_validate,
        )
        with self.assertLogs(level="INFO") as cm:
            cli.process(man)

        # Assert log is called with expected error messages
        # Not going to try and assert equality on the full log as it contains a
        # stack-trace
        self.assertIn("ERROR:root:Unable to parse data into CSV.", cm.output)

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
        self.assertEqual(
            man.clean_data,
            {
                "1": [["a", "b"], [1, 2], [4, 5], [7, 8]],
                "2": None,
                "3": [["no2", "co2"], [12, 14]],
            },
        )

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
                [["a", "b"], [1, 2], [4, 5], [7, 8]],
                [["no2", "co2"], [12, 14]],
            ]
        )

        man = Mock(
            device_ids=["1", "2", "3"],
            device_web_ids=["4", "5", "6"],
            raw_data={"1": [1, 2, 3], "2": [8, 10], "3": ["foo", "bar"]},
            clean_data={},
            parse_to_csv=mock_parse,
            validate_data=mock_validate,
        )
        with self.assertLogs(level="INFO") as cm:
            cli.process(man)

        # Assert log is called with expected error messages
        # Not going to try and assert equality on the full log as it contains a
        # stack-trace
        self.assertIn(
            "ERROR:root:No time-points have been found in the parsed CSV.", cm.output
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
        self.assertEqual(
            man.clean_data,
            {
                "1": [["a", "b"], [1, 2], [4, 5], [7, 8]],
                "2": None,
                "3": [["no2", "co2"], [12, 14]],
            },
        )

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
                utils.ValidateDataError(""),
                [["foo", "bar"], [4, 2], [4, 1]],
                [["no2", "co2"], [12, 14]],
            ]
        )

        man = Mock(
            device_ids=["1", "2", "3"],
            device_web_ids=["4", "5", "6"],
            raw_data={"1": [1, 2, 3], "2": [8, 10], "3": ["foo", "bar"]},
            clean_data={},
            parse_to_csv=mock_parse,
            validate_data=mock_validate,
        )
        with self.assertLogs(level="INFO") as cm:
            cli.process(man)

        # Assert log is called with expected error messages
        # Not going to try and assert equality on the full log as it contains a
        # stack-trace
        self.assertIn(
            "ERROR:root:Something went wrong during data validation.", cm.output
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
        self.assertEqual(
            man.clean_data,
            {
                "1": None,
                "2": [["foo", "bar"], [4, 2], [4, 1]],
                "3": [["no2", "co2"], [12, 14]],
            },
        )
