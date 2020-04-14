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

from unittest.mock import patch, MagicMock, Mock, call, mock_open

# Test parse_args:
#    - is this needed? Is it possible to test CLI arguments through unit testing?
#    - more appropriate to keep parse_args() as a function and make a
#    parse_config() function, that:
#       - has args filepath, and returns config object
#       - it also performs basic QA, ensuring the filepath exists and the INI is
#       formatted correctly
#   - can then test this parse_config() function

# Test setup_scraping_timeline:
#   - how to test this automatically? requires knowing yesterday's date, which
#     is obviously dependent upon the date the test is run. To generate expected
#     outputs, I would end up rewriting the same logic that the function uses.
#     Thereby defeating point of testing
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
