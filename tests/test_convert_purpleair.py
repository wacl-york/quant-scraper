"""
    test_convert_purpleair.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Unit tests for the quantscraper/convert_purpleair.py script.
"""

import unittest
from unittest.mock import patch, Mock, call
import datetime
import pandas as pd
import numpy as np
import quantscraper.utils as utils
from quantscraper.manufacturers.PurpleAir import PurpleAir
import quantscraper.convert_purpleair as convert_purpleair


class TestInstantiatePAManufacturer(unittest.TestCase):
    def test_success(self):
        config = {
            "Data": "foo",
            "manufacturers": [
                {
                    "name": "PurpleAir",
                    "properties": {
                        "timestamp_column": "time",
                        "timestamp_format": "%Y",
                        "recording_frequency_per_hour": 45,
                    },
                    "devices": [
                        {"id": "R2-D2", "webid": "webR2", "location": "Tattooine"},
                        {"id": "C3-P0", "webid": "webC3", "location": "YavinIV"},
                    ],
                    "fields": [
                        {
                            "id": "CO2",
                            "webid": "co2_raw",
                            "scale": 5,
                            "include_analysis": True,
                        }
                    ],
                },
                {
                    "name": "Aeroqual",
                    "properties": {
                        "timestamp_column": "timepoint",
                        "timestamp_format": "%M",
                        "recording_frequency_per_hour": 60,
                    },
                    "devices": [
                        {"id": "Cat", "webid": "Tabby", "location": "Garden"},
                        {"id": "Dog", "webid": "Spaniel", "location": "Kennel"},
                    ],
                    "fields": [
                        {
                            "id": "NO2",
                            "webid": "no2_raw",
                            "scale": 2,
                            "include_analysis": False,
                        }
                    ],
                },
            ],
        }
        with patch(
            "quantscraper.convert_purpleair.utils.load_device_configuration",
            return_value=config,
        ):
            res = convert_purpleair.instantiate_PA_manufacturer()
            self.assertIsInstance(res, PurpleAir)

    def test_doesnt_parse(self):
        # Missing properties attribute so won't instantiate
        config = {
            "Data": "foo",
            "manufacturers": [
                {
                    "name": "PurpleAir",
                    "devices": [
                        {"id": "R2-D2", "webid": "webR2", "location": "Tattooine"},
                        {"id": "C3-P0", "webid": "webC3", "location": "YavinIV"},
                    ],
                    "fields": [
                        {
                            "id": "CO2",
                            "webid": "co2_raw",
                            "scale": 5,
                            "include_analysis": True,
                        }
                    ],
                },
                {
                    "name": "Aeroqual",
                    "properties": {
                        "timestamp_column": "timepoint",
                        "timestamp_format": "%M",
                        "recording_frequency_per_hour": 60,
                    },
                    "devices": [
                        {"id": "Cat", "webid": "Tabby", "location": "Garden"},
                        {"id": "Dog", "webid": "Spaniel", "location": "Kennel"},
                    ],
                    "fields": [
                        {
                            "id": "NO2",
                            "webid": "no2_raw",
                            "scale": 2,
                            "include_analysis": False,
                        }
                    ],
                },
            ],
        }
        with patch(
            "quantscraper.convert_purpleair.utils.load_device_configuration",
            return_value=config,
        ):
            res = convert_purpleair.instantiate_PA_manufacturer()
            self.assertIsNone(res)

    def test_no_pa_manufacturer(self):
        # No PA manufacturer in config
        config = {
            "Data": "foo",
            "manufacturers": [
                {
                    "name": "Aeroqual",
                    "properties": {
                        "timestamp_column": "timepoint",
                        "timestamp_format": "%M",
                        "recording_frequency_per_hour": 60,
                    },
                    "devices": [
                        {"id": "Cat", "webid": "Tabby", "location": "Garden"},
                        {"id": "Dog", "webid": "Spaniel", "location": "Kennel"},
                    ],
                    "fields": [
                        {
                            "id": "NO2",
                            "webid": "no2_raw",
                            "scale": 2,
                            "include_analysis": False,
                        }
                    ],
                }
            ],
        }
        with patch(
            "quantscraper.convert_purpleair.utils.load_device_configuration",
            return_value=config,
        ):
            res = convert_purpleair.instantiate_PA_manufacturer()
            self.assertIsNone(res)


class TestParseArgs(unittest.TestCase):
    def test_success(self):
        # Just confirm that expected calls are made
        with patch(
            "quantscraper.convert_purpleair.argparse.ArgumentParser"
        ) as mock_ArgumentParser:
            mock_addargument = Mock()
            mock_args = Mock
            mock_parseargs = Mock(return_value=mock_args)
            mock_parser = Mock(add_argument=mock_addargument, parse_args=mock_parseargs)
            mock_ArgumentParser.return_value = mock_parser

            res = convert_purpleair.parse_args()

            self.assertEqual(res, mock_args)
            mock_ArgumentParser.assert_called_once_with(
                description="Convert raw PurpleAir data to QUANT format"
            )

            actual_addargument_calls = mock_addargument.mock_calls
            exp_addargument_calls = [
                call(
                    "--recipients",
                    metavar="EMAIL@DOMAIN",
                    nargs="+",
                    help="The recipients to send the email to.",
                ),
                call(
                    "--gdrive-clean-id",
                    help="Google Drive clean data folder to upload to. If not provided then files aren't uploaded.",
                ),
                call(
                    "--gdrive-availability-id",
                    help="Google Drive availability data folder to upload to. If not provided then availability logs aren't uploaded.",
                ),
                call(
                    "--gdrive-pa-id",
                    help="Google Drive staging folder where PurpleAir files are manually uploaded to.",
                    required=True,
                ),
                call(
                    "--gdrive-quant-shared-id",
                    help="Id of QUANT Shared Drive.",
                    required=True,
                ),
            ]
            self.assertEqual(actual_addargument_calls, exp_addargument_calls)

            mock_parseargs.assert_called_once_with()


class TestUploadData(unittest.TestCase):
    def setUp(self):
        self.mock_service = Mock()
        self.folder_id = "123#456"
        self.data = [
            ["Timestamps", "B", "C"],
            ["2020-03-04", "2", "3"],
            ["2020-03-02", "5", "6"],
        ]
        self.fn = "mydata2.csv"

    def test_success(self):
        # patch save_data
        with patch("quantscraper.cli.utils.save_csv_file") as mock_save_csv:

            # patch upload_file_google_drive
            with patch(
                "quantscraper.cli.utils.upload_file_google_drive"
            ) as mock_upload:

                res = convert_purpleair.upload_data(
                    self.data, self.fn, self.folder_id, self.mock_service
                )

                mock_save_csv.assert_called_once_with(self.data, "mydata2.csv")
                mock_upload.assert_called_once_with(
                    self.mock_service, self.fn, self.folder_id, "text/csv"
                )
                self.assertTrue(res)

    def test_upload_error(self):
        # If error in upload should return False
        with patch("quantscraper.cli.utils.save_csv_file") as mock_save_csv:
            with patch(
                "quantscraper.cli.utils.upload_file_google_drive",
                side_effect=utils.DataUploadError(""),
            ) as mock_upload:

                res = convert_purpleair.upload_data(
                    self.data, self.fn, self.folder_id, self.mock_service
                )

                mock_save_csv.assert_called_once_with(self.data, "mydata2.csv")
                mock_upload.assert_called_once_with(
                    self.mock_service, self.fn, self.folder_id, "text/csv"
                )
                self.assertFalse(res)

    def test_save_error(self):
        # If error in saving should return False and upload shouldn't be called

        with patch(
            "quantscraper.cli.utils.save_csv_file",
            side_effect=utils.DataSavingError(""),
        ) as mock_save_csv:
            with patch(
                "quantscraper.cli.utils.upload_file_google_drive",
                side_effect=utils.DataUploadError(""),
            ) as mock_upload:

                res = convert_purpleair.upload_data(
                    self.data, self.fn, self.folder_id, self.mock_service
                )

                mock_save_csv.assert_called_once_with(self.data, "mydata2.csv")
                self.assertFalse(mock_upload.called)
                self.assertFalse(res)


class TestTabularSummary(unittest.TestCase):
    def test_success(self):
        summaries = {
            "2020-03-04": {
                "dev1": {"co2": 100, "no": 292, "timestamp": 310},
                "dev2": {"co2": 120, "no": 188, "timestamp": 240},
            },
            "2020-05-01": {
                "dev1": {"o3": 328, "no": 423, "timestamp": 500,},
                "dev3": {"o3": 0, "no": 0, "timestamp": 0},
            },
        }

        exp = {
            "2020-03-04": [
                ["Device ID", "Timestamps", "co2", "no"],
                ["dev1", "310 (43%)", "100 (14%)", "292 (41%)"],
                ["dev2", "240 (33%)", "120 (17%)", "188 (26%)"],
            ],
            "2020-05-01": [
                ["Device ID", "Timestamps", "no", "o3"],
                ["dev1", "500 (69%)", "423 (59%)", "328 (46%)"],
                ["dev3", "0 (0%)", "0 (0%)", "0 (0%)"],
            ],
        }
        res = convert_purpleair.tabular_summary(summaries, 30)
        self.assertEqual(res, exp)

    def test_rate(self):
        # Test with a different rate
        summaries = {
            "2020-03-04": {
                "dev1": {"co2": 100, "no": 292, "timestamp": 310},
                "dev2": {"co2": 120, "no": 188, "timestamp": 240},
            },
            "2020-05-01": {
                "dev1": {"o3": 328, "no": 423, "timestamp": 500,},
                "dev3": {"o3": 0, "no": 0, "timestamp": 0},
            },
        }

        exp = {
            "2020-03-04": [
                ["Device ID", "Timestamps", "co2", "no"],
                ["dev1", "310 (22%)", "100 (7%)", "292 (20%)"],
                ["dev2", "240 (17%)", "120 (8%)", "188 (13%)"],
            ],
            "2020-05-01": [
                ["Device ID", "Timestamps", "no", "o3"],
                ["dev1", "500 (35%)", "423 (29%)", "328 (23%)"],
                ["dev3", "0 (0%)", "0 (0%)", "0 (0%)"],
            ],
        }
        res = convert_purpleair.tabular_summary(summaries, 60)
        self.assertEqual(res, exp)

    def test_no_measurands(self):
        # When no measurands in input summaries should get empty columns
        # Have removed CO2 from dev2 in first entry and o3 from dev1 in second
        summaries = {
            "2020-03-04": {
                "dev1": {"co2": 100, "no": 292, "timestamp": 310},
                "dev2": {"no": 188, "timestamp": 240},
            },
            "2020-05-01": {
                "dev1": {"no": 423, "timestamp": 500,},
                "dev3": {"o3": 0, "no": 0, "timestamp": 0},
            },
        }

        exp = {
            "2020-03-04": [
                ["Device ID", "Timestamps", "co2", "no"],
                ["dev1", "310 (22%)", "100 (7%)", "292 (20%)"],
                ["dev2", "240 (17%)", "", "188 (13%)"],
            ],
            "2020-05-01": [
                ["Device ID", "Timestamps", "no", "o3"],
                ["dev1", "500 (35%)", "423 (29%)", ""],
                ["dev3", "0 (0%)", "0 (0%)", "0 (0%)"],
            ],
        }
        res = convert_purpleair.tabular_summary(summaries, 60)
        self.assertEqual(res, exp)

    def test_no_timestamp(self):
        # Likewise no timestamp available should make the associated column
        # empty
        # Have removed timestamp from dev1 in first entry and dev3 in second
        summaries = {
            "2020-03-04": {
                "dev1": {"co2": 100, "no": 292},
                "dev2": {"co2": 120, "no": 188, "timestamp": 240},
            },
            "2020-05-01": {
                "dev1": {"o3": 328, "no": 423, "timestamp": 500,},
                "dev3": {"o3": 0, "no": 0},
            },
        }

        exp = {
            "2020-03-04": [
                ["Device ID", "Timestamps", "co2", "no"],
                ["dev1", "", "100 (7%)", "292 (20%)"],
                ["dev2", "240 (17%)", "120 (8%)", "188 (13%)"],
            ],
            "2020-05-01": [
                ["Device ID", "Timestamps", "no", "o3"],
                ["dev1", "500 (35%)", "423 (29%)", "328 (23%)"],
                ["dev3", "", "0 (0%)", "0 (0%)"],
            ],
        }
        res = convert_purpleair.tabular_summary(summaries, 60)
        self.assertEqual(res, exp)


class TestGetDateFromPurpleAirFn(unittest.TestCase):
    # PurpleAir dates are in format %Y%m%d by default, although this can be
    # specified through an argument
    # The filenames are simply <date>.csv

    def test_success(self):
        # Should return None if no date or format not recognised.
        # Can specify output format through second arg
        self.assertEqual(
            convert_purpleair.get_date_from_purpleair_fn("19820903.csv", "%Y-%m-%d"),
            "1982-09-03",
        )
        self.assertEqual(
            convert_purpleair.get_date_from_purpleair_fn(
                "foo/bar/20200301.csv", "%Y-%m-%d"
            ),
            "2020-03-01",
        )
        self.assertEqual(
            convert_purpleair.get_date_from_purpleair_fn(
                "foo/bar/20200301.csv", "%Y-%b-%d"
            ),
            "2020-Mar-01",
        )
        # No date = error, returns None
        self.assertIsNone(
            convert_purpleair.get_date_from_purpleair_fn(
                "PA_03_20200321.csv", "%Y-%m-%d"
            )
        )
        # Date in incorrect format, returns None
        self.assertIsNone(
            convert_purpleair.get_date_from_purpleair_fn("2020-03-04csv", "%Y-%m-%d"),
        )

        # Can specify PA date format
        self.assertEqual(
            convert_purpleair.get_date_from_purpleair_fn(
                "1972-09-23.csv", "%Y%m%d", pa_date_format="%Y-%m-%d"
            ),
            "19720923",
        )
        # And it returns None when format doesn't match
        self.assertIsNone(
            convert_purpleair.get_date_from_purpleair_fn(
                "19720923.csv", "%Y%m%d", pa_date_format="%Y-%m-%d"
            )
        )


class TestConvertToCleanFn(unittest.TestCase):
    def test_success(self):
        # Should return None if no date or format not recognised.
        self.assertEqual(
            convert_purpleair.convert_to_clean_fn("19820903.csv", "PAAB", "%Y-%m-%d"),
            "PurpleAir_PAAB_1982-09-03.csv",
        )

        self.assertEqual(
            convert_purpleair.convert_to_clean_fn("19820903.csv", "PA_AB", "%Y-%m-%d"),
            "PurpleAir_PA_AB_1982-09-03.csv",
        )

        self.assertEqual(
            convert_purpleair.convert_to_clean_fn("20201104.csv", "PA_AB", "%Y-%b-%d"),
            "PurpleAir_PA_AB_2020-Nov-04.csv",
        )

        self.assertEqual(
            convert_purpleair.convert_to_clean_fn("19201030.csv", "", "%Y-%d"),
            "PurpleAir__1920-30.csv",
        )

        # Returns None if can't parse date according to PA format
        self.assertIsNone(
            convert_purpleair.convert_to_clean_fn("1920-03-04.csv", "", "%Y-%d")
        )

        self.assertIsNone(
            convert_purpleair.convert_to_clean_fn(
                "PA_04_19200329.csv", "PA_04", "%Y-%m-%d"
            )
        )
