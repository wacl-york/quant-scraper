"""
    test_purpleair_preprocessing.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Unit tests for the quantscraper/preprocess_purpleair.py script.
"""

import unittest
from unittest.mock import patch, Mock, call
import datetime
import pandas as pd
import numpy as np
import quantscraper.utils as utils
import quantscraper.preprocess_purpleair as preprocess_purpleair


class TestGetAvailableCleanDates(unittest.TestCase):
    def test_success(self):
        with patch("quantscraper.preprocess_purpleair.glob") as mock_glob:
            fake_fns = [
                "PurpleAir_PA05_2020-04-28.csv",
                "PurpleAir_PA05_2020-01-28.csv",
                "PurpleAir_PA05_2019-03-01.csv",
            ]

            exp_dates = [
                "2019-03-01",
                "2020-01-28",
                "2020-04-28",
            ]
            glob_func = Mock(return_value=fake_fns)
            mock_glob.glob = glob_func
            res = preprocess_purpleair.get_available_clean_dates("foo/bar")

            glob_func.assert_called_once_with("foo/bar/PurpleAir*")
            self.assertEqual(sorted(res), sorted(exp_dates))

    def test_incorrect_date(self):
        # This function shouldn't check if date is valid date, so should return
        # the 52nd January 2020 here
        with patch("quantscraper.preprocess_purpleair.glob") as mock_glob:
            fake_fns = [
                "PurpleAir_PA05_2020-04-28.csv",
                "PurpleAir_PA05_2020-01-52.csv",
                "PurpleAir_PA05_2019-03-01.csv",
            ]

            exp_dates = ["2019-03-01", "2020-01-52", "2020-04-28"]
            glob_func = Mock(return_value=fake_fns)
            mock_glob.glob = glob_func
            res = preprocess_purpleair.get_available_clean_dates("foo/bar")

            glob_func.assert_called_once_with("foo/bar/PurpleAir*")
            self.assertEqual(sorted(res), sorted(exp_dates))

    def test_no_date(self):
        # If don't have a parseable date, then skip this file
        with patch("quantscraper.preprocess_purpleair.glob") as mock_glob:
            fake_fns = [
                "PurpleAir_PA05_2020-04-28.csv",
                "PurpleAir_somethinginvalid.csv",
                "PurpleAir_PA05_2019-03-01.csv",
            ]

            exp_dates = ["2019-03-01", "2020-04-28"]
            glob_func = Mock(return_value=fake_fns)
            mock_glob.glob = glob_func
            res = preprocess_purpleair.get_available_clean_dates("foo/bar")

            glob_func.assert_called_once_with("foo/bar/PurpleAir*")
            self.assertEqual(sorted(res), sorted(exp_dates))


class TestGetDateFromCleanFn(unittest.TestCase):
    def test_success(self):
        # Should return None if no date or format not recognised.
        # Shouldn't attempted to parse date however
        self.assertEqual(
            preprocess_purpleair.get_date_from_clean_fn(
                "foo/bar/Man_Dev_2020-03-01.csv"
            ),
            "2020-03-01",
        )
        self.assertEqual(
            preprocess_purpleair.get_date_from_clean_fn(
                "foo/bar/Man_Dev_150-04-52.csv"
            ),
            "150-04-52",
        )
        self.assertEqual(
            preprocess_purpleair.get_date_from_clean_fn("foo/bar/Man_Dev_FoF.csv"),
            "FoF",
        )
        self.assertEqual(
            preprocess_purpleair.get_date_from_clean_fn("Man_Dev_2003-04-29.csv"),
            "2003-04-29",
        )
        self.assertEqual(
            preprocess_purpleair.get_date_from_clean_fn("Man_summary.csv"), None
        )


class TestGetDateFromAnalysisFn(unittest.TestCase):
    def test_success(self):
        # Should return None if no date or format not recognised.
        # Shouldn't attempted to parse date however
        self.assertEqual(
            preprocess_purpleair.get_date_from_analysis_fn(
                "foo/bar/Man_2020-03-01.csv"
            ),
            "2020-03-01",
        )
        self.assertEqual(
            preprocess_purpleair.get_date_from_analysis_fn("foo/bar/Man_150-04-52.csv"),
            "150-04-52",
        )
        self.assertEqual(
            preprocess_purpleair.get_date_from_analysis_fn("foo/bar/Man_FoF.csv"), "FoF"
        )
        self.assertEqual(
            preprocess_purpleair.get_date_from_analysis_fn("Man_2003-04-29.csv"),
            "2003-04-29",
        )
        self.assertEqual(
            preprocess_purpleair.get_date_from_analysis_fn("Man.csv"), None
        )


class TestPADeviceIDs(unittest.TestCase):
    def test_success(self):
        config = {
            "Data": "foo",
            "manufacturers": [
                {
                    "name": "PurpleAir",
                    "stats": [1, 2, 3],
                    "devices": [
                        {"id": "R2-D2", "webid": "webR2", "location": "Tattooine"},
                        {"id": "C3-P0", "webid": "webC3", "location": "YavinIV"},
                    ],
                },
                {
                    "name": "Aeroqual",
                    "stats": [1, 2, 3],
                    "devices": [
                        {"id": "Cat", "webid": "Tabby", "location": "Garden"},
                        {"id": "Dog", "webid": "Spaniel", "location": "Kennel"},
                    ],
                },
            ],
        }

        res = preprocess_purpleair.get_pa_device_ids(config)
        self.assertEqual(res, ["R2-D2", "C3-P0"])
