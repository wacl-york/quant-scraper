"""
    test_cli.py
    ~~~~~~~~~~~

    Unit tests for cli functions.
"""

import datetime
import unittest
import configparser
import quantscraper.cli as cli
import quantscraper.utils as utils
import logging
import time
from io import StringIO

from unittest.mock import patch, MagicMock, Mock, call

# Test parse_args:
#    - is this needed? Is it possible to test CLI arguments through unit testing?
#    - more appropriate to keep parse_args() as a function and make a
#    parse_config() function, that:
#       - has args filepath, and returns config object
#       - it also performs basic QA, ensuring the filepath exists and the INI is
#       formatted correctly
#   - can then test this parse_config() function


class TestSetupLoggers(unittest.TestCase):
    # Capturing the log output is relatively tricky without a 3rd party library.
    # This would be ideal to check that the log format is as expected, but not
    # worth the additional dependency and test complexity for now.
    # Instead will just ensure the setup is as expected.

    def test_logger(self):
        # By default, logger is set to warn (30) and has no handlers
        logger = logging.getLogger()
        self.assertEqual(logger.getEffectiveLevel(), 30)
        self.assertFalse(logger.hasHandlers())

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


# Test setup_loggers:
#   Not essential for now
#   But can test format
