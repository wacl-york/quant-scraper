"""
    test_utils.py
    ~~~~~~~~~~~~~~

    Unit tests for utility functions found in quantscraper.utils
"""

import unittest
import string
import os
from unittest.mock import patch, Mock, mock_open
import pandas as pd
from googleapiclient.errors import HttpError
from utils import build_mock_response

import quantscraper.utils as utils


class TestSetupConfig(unittest.TestCase):

    # Ensures the expected calls are made
    def test_success(self):
        with patch("quantscraper.utils.configparser") as mock_cp:
            mock_read = Mock()
            mock_sections = Mock(return_value=[1, 2, 3])

            mock_cfginstance = Mock(sections=mock_sections, read=mock_read)
            mock_ConfigParser = Mock(return_value=mock_cfginstance)
            mock_cp.ConfigParser = mock_ConfigParser

            res = utils.setup_config("foo.ini")

            self.assertEqual(res, mock_cfginstance)
            mock_read.assert_called_once_with("foo.ini")

    def test_errorraised_no_sections(self):
        with patch("quantscraper.utils.configparser") as mock_cp:
            mock_read = Mock()
            mock_sections = Mock(return_value=[])

            mock_cfginstance = Mock(sections=mock_sections, read=mock_read)
            mock_ConfigParser = Mock(return_value=mock_cfginstance)
            mock_cp.ConfigParser = mock_ConfigParser

            with self.assertRaises(utils.SetupError):
                utils.setup_config("foo.ini")


class TestIsFloat(unittest.TestCase):
    # Test utils.is_float() function

    def test_float(self):
        self.assertTrue(utils.is_float("5.23"))

    def test_exponent(self):
        self.assertTrue(utils.is_float("2e2"))

    def test_exponent2(self):
        self.assertTrue(utils.is_float("-1.5e5"))

    def test_exponent_inf(self):
        self.assertFalse(utils.is_float("-1.5e5000"))

    def test_negative_float(self):
        self.assertTrue(utils.is_float("-8.03"))

    def test_int(self):
        self.assertTrue(utils.is_float("83"))

    def test_negative_int(self):
        self.assertTrue(utils.is_float("-232"))

    def test_0_int(self):
        self.assertTrue(utils.is_float("0"))

    def test_0_float(self):
        self.assertTrue(utils.is_float("0.0"))

    def test_negative_0_int(self):
        self.assertTrue(utils.is_float("-0"))

    def test_negative_0_float(self):
        self.assertTrue(utils.is_float("-0.0"))

    def test_inf(self):
        self.assertFalse(utils.is_float("Inf"))

    def test_inf2(self):
        self.assertFalse(utils.is_float("INF"))

    def test_inf3(self):
        self.assertFalse(utils.is_float("INFINITY"))

    def test_inf4(self):
        self.assertFalse(utils.is_float("inf"))

    def test_negative_inf(self):
        self.assertFalse(utils.is_float("-Inf"))

    def test_negative_inf2(self):
        self.assertFalse(utils.is_float("-INF"))

    def test_negative_inf3(self):
        self.assertFalse(utils.is_float("-INFINITY"))

    def test_negative_inf4(self):
        self.assertFalse(utils.is_float("-inf"))

    def test_nan(self):
        self.assertFalse(utils.is_float("Nan"))

    def test_nan2(self):
        self.assertFalse(utils.is_float("NAN"))

    def test_nan3(self):
        self.assertFalse(utils.is_float("NaN"))

    def test_nan4(self):
        self.assertFalse(utils.is_float("nan"))

    def test_negative_nan(self):
        self.assertFalse(utils.is_float("-Nan"))

    def test_negative_nan2(self):
        self.assertFalse(utils.is_float("-NAN"))

    def test_negative_nan3(self):
        self.assertFalse(utils.is_float("-NaN"))

    def test_negative_nan4(self):
        self.assertFalse(utils.is_float("-nan"))

    def test_special_char(self):
        self.assertFalse(utils.is_float("%%1"))

    def test_special_char2(self):
        self.assertFalse(utils.is_float("1%"))

    def test_special_char3(self):
        self.assertFalse(utils.is_float("{}.format(2)"))

    def test_none(self):
        self.assertFalse(utils.is_float("None"))

    def test_false(self):
        self.assertFalse(utils.is_float("False"))

    def test_false2(self):
        self.assertFalse(utils.is_float("false"))

    def test_true(self):
        self.assertFalse(utils.is_float("True"))

    def test_true2(self):
        self.assertFalse(utils.is_float("true"))


class TestAuthGoogleAPI(unittest.TestCase):
    # the utils.auth_google_api method should return a connection to Google
    # Drive's API

    def test_no_env_var(self):
        with patch(
            "quantscraper.utils.service_account.Credentials.from_service_account_info"
        ) as mock_cred_obj:
            with self.assertRaises(utils.GoogleAPIError):
                utils.auth_google_api()

    def test_envvar_format_error(self):
        # Poorly formatted JSON
        os.environ["GOOGLE_CREDS"] = '{"foo": "bar"'
        with patch(
            "quantscraper.utils.service_account.Credentials.from_service_account_info"
        ) as mock_cred_obj:
            with self.assertRaises(utils.GoogleAPIError):
                utils.auth_google_api()

    def test_success(self):
        # Patch credentials call
        os.environ["GOOGLE_CREDS"] = '{"foo": "bar", "alpha": 3.5}'

        with patch(
            "quantscraper.utils.service_account.Credentials.from_service_account_info"
        ) as mock_cred_obj:
            mock_credentials = Mock()
            mock_cred_obj.return_value = mock_credentials

            # Patch service builder
            with patch(
                "quantscraper.utils.googleapiclient.discovery.build"
            ) as mock_build:
                mock_service = Mock()
                mock_build.return_value = mock_service

                service = utils.auth_google_api()

                # Using standard recommended google drive scope
                exp_scopes = ["https://www.googleapis.com/auth/drive.file"]

                # Test calls
                mock_cred_obj.assert_called_once_with(
                    dict(foo="bar", alpha=3.5), scopes=exp_scopes
                )
                mock_build.assert_called_once_with(
                    "drive", "v3", credentials=mock_credentials, cache_discovery=False
                )
                self.assertEqual(service, mock_service)


class TestUploadFileGoogleDrive(unittest.TestCase):
    # the utils.upload_file_google_drive function uploads a single
    # file to Google Drive.

    def test_success(self):
        with patch("quantscraper.utils.MediaFileUpload") as mock_mediafile:
            mock_media = Mock()
            mock_mediafile.return_value = mock_media

            # Setup the services.files().create().execute() mock pipeline
            mock_execute = Mock()
            mock_create = Mock(return_value=Mock(execute=mock_execute))
            mock_files = Mock(return_value=Mock(create=mock_create))
            mock_service = Mock(files=mock_files)

            utils.upload_file_google_drive(
                mock_service, "drive1/drive2/foo.txt", "123foo", "text/foobar"
            )

            # Test calls are as expected
            mock_mediafile.assert_called_once_with(
                "drive1/drive2/foo.txt", mimetype="text/foobar"
            )
            mock_create.assert_called_once_with(
                body={
                    "name": "foo.txt",
                    "mimeType": "text/foobar",
                    "parents": ["123foo"],
                },
                media_body=mock_media,
                supportsAllDrives=True,
            )

    def test_httperror(self):
        with patch("quantscraper.utils.MediaFileUpload") as mock_mediafile:
            # with patch("quantscraper.utils.HttpError") as mock_httperror:
            mock_media = Mock()
            mock_mediafile.return_value = mock_media

            # Setup the services.files().create().execute() mock pipeline
            mock_resp = build_mock_response(status=400)
            mock_execute = Mock(side_effect=HttpError(mock_resp, b""))
            mock_create = Mock(return_value=Mock(execute=mock_execute))
            mock_files = Mock(return_value=Mock(create=mock_create))
            mock_service = Mock(files=mock_files)

            with self.assertRaises(utils.DataUploadError):
                utils.upload_file_google_drive(
                    mock_service, "drive1/drive2/foo.txt", "123foo", "text/foobar"
                )


class TestSaveCSVFile(unittest.TestCase):
    # Tests utils.save_csv_file, which writes a 2D list to CSV

    def test_success(self):
        m = mock_open()

        # Save file to specified folder with filename template:
        with patch("quantscraper.utils.open", m):
            # Need to patch os.path to force file to not exist
            with patch("quantscraper.utils.os.path") as mock_path:
                mock_path.isfile = Mock(return_value=False)
                # patch CSV and mock csv.writer
                with patch("quantscraper.utils.csv") as mock_csv:
                    mock_writer = Mock()
                    mock_writerows = Mock()
                    mock_writer.return_value = Mock(writerows=mock_writerows)
                    mock_csv.writer = mock_writer

                    utils.save_csv_file([[1, 2, 3], [4, 5, 6]], "path/to/fn.csv")
                    # Check calls are as expected
                    m.assert_called_once_with("path/to/fn.csv", "w")
                    mock_writer.assert_called_once_with(m(), delimiter=",")
                    mock_writerows.assert_called_once_with([[1, 2, 3], [4, 5, 6]])

    def test_file_exists(self):
        # Check that the DataSavingError is raised when file exists
        m = mock_open()

        with patch("quantscraper.utils.open", m):
            # Mock file existing
            with patch("quantscraper.utils.os.path") as mock_path:
                mock_path.isfile = Mock(return_value=True)

                with self.assertRaises(utils.DataSavingError):
                    utils.save_csv_file([[1, 2, 3], [4, 5, 6]], "path/to/fn.csv")

    def test_dir_doesnt_exist(self):
        m = mock_open()
        # open raises FileNotFoundError if dir doesn't exist
        m.side_effect = FileNotFoundError()

        # Save file to specified folder with filename template:
        with patch("quantscraper.utils.open", m):
            # Need to patch os.path to force file to not exist
            with patch("quantscraper.utils.os.path") as mock_path:
                mock_path.isfile = Mock(return_value=False)
                # patch CSV and mock csv.writer
                with patch("quantscraper.utils.csv") as mock_csv:
                    mock_writer = Mock()
                    mock_writerows = Mock()
                    mock_writer.return_value = Mock(writerows=mock_writerows)
                    mock_csv.writer = mock_writer

                    with self.assertRaises(utils.DataSavingError):
                        utils.save_csv_file([[1, 2, 3], [4, 5, 6]], "path/to/fn.csv")


class TestSaveJSONFile(unittest.TestCase):
    # Tests utils.save_json_file, which writes Python object to JSON file
    # Unfortunately can't mock JSONDecodeError to assert this error is handled
    # correctly, as the error needs to be instantiated which I can't mock.
    # However, I have tested this functionality by running the program
    # interactively

    def test_success(self):
        m = mock_open()

        # Save file to specified folder with filename template:
        with patch("quantscraper.utils.open", m):
            # Need to patch os.path to force file to not exist
            with patch("quantscraper.utils.os.path") as mock_path:
                mock_path.isfile = Mock(return_value=False)
                # patch json
                with patch("quantscraper.utils.json") as mock_json:
                    mock_dump = Mock()
                    mock_json.dump = mock_dump

                    utils.save_json_file([[1, 2, 3], [4, 5, 6]], "path/to/fn.json")
                    # Check calls are as expected
                    m.assert_called_once_with("path/to/fn.json", "w")
                    mock_dump.assert_called_once_with([[1, 2, 3], [4, 5, 6]], m())

    def test_file_exists(self):
        # Check that the DataSavingError is raised when file exists
        m = mock_open()

        with patch("quantscraper.utils.open", m):
            # Mock file existing
            with patch("quantscraper.utils.os.path") as mock_path:
                mock_path.isfile = Mock(return_value=True)

                with self.assertRaises(utils.DataSavingError):
                    utils.save_json_file([[1, 2, 3], [4, 5, 6]], "path/to/fn.json")

    def test_dir_doesnt_exist(self):
        # Check that the DataSavingError is raised when dir doesn't exist,
        # which raises a FileNotFoundError
        m = mock_open()
        m.side_effect = FileNotFoundError()

        with patch("quantscraper.utils.open", m):
            # Mock file existing
            with patch("quantscraper.utils.os.path") as mock_path:
                mock_path.isfile = Mock(return_value=True)

                with self.assertRaises(utils.DataSavingError):
                    utils.save_json_file([[1, 2, 3], [4, 5, 6]], "path/to/fn.json")


class TestSaveDataFrame(unittest.TestCase):
    # Tests utils.save_dataframe function, which writes a pandas.DataFrame to disk
    def test_success(self):
        dummy_data = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        # Need to patch os.path to force file to not exist
        with patch("quantscraper.utils.os.path") as mock_path:
            mock_path.isfile = Mock(return_value=False)
            with patch.object(pd.DataFrame, "to_csv") as mock_to_csv:
                utils.save_dataframe(dummy_data, "path/to/fn.csv")
                # Check calls is as expected
                mock_to_csv.assert_called_once_with("path/to/fn.csv")

    def test_file_exists(self):
        dummy_data = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        # Check that the DataSavingError is raised when file exists
        with patch("quantscraper.utils.os.path") as mock_path:
            mock_path.isfile = Mock(return_value=True)

            with self.assertRaises(utils.DataSavingError):
                utils.save_dataframe(dummy_data, "path/to/fn.csv")

    def test_dir_doesnt_exist(self):
        # If dir doesn't exist a FileNotFoundError is raised
        dummy_data = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        # Need to patch os.path to force file to not exist
        with patch("quantscraper.utils.os.path") as mock_path:
            mock_path.isfile = Mock(return_value=False)
            with patch.object(pd.DataFrame, "to_csv") as mock_to_csv:
                mock_to_csv.side_effect = FileNotFoundError()

                with self.assertRaises(utils.DataSavingError):
                    utils.save_dataframe(dummy_data, "path/to/fn.csv")


class TestSavePlaintext(unittest.TestCase):

    # Tests utils.save_plaintext function, which writes a string to disk
    def test_success(self):
        m = mock_open()

        dummy_text = "foobar\ncar"

        # Save file to specified folder with filename template:
        with patch("quantscraper.utils.open", m):
            # Need to patch os.path to force file to not exist
            with patch("quantscraper.utils.os.path") as mock_path:
                mock_path.isfile = Mock(return_value=False)

                utils.save_plaintext(dummy_text, "path/to/fn.txt")
                # Check calls are as expected
                m.assert_called_once_with("path/to/fn.txt", "w")

    def test_file_exists(self):
        # Check that the DataSavingError is raised when file exists
        m = mock_open()
        dummy_text = "foobar\ncar"
        with patch("quantscraper.utils.open", m):
            # Mock file existing
            with patch("quantscraper.utils.os.path") as mock_path:
                mock_path.isfile = Mock(return_value=True)

                with self.assertRaises(utils.DataSavingError):
                    utils.save_plaintext(dummy_text, "path/to/fn.txt")

    def test_dir_doesnt_exist(self):
        m = mock_open()
        # open raises FileNotFoundError if dir doesn't exist
        m.side_effect = FileNotFoundError()
        dummy_text = "foobar\ncar"

        # Save file to specified folder with filename template:
        with patch("quantscraper.utils.open", m):
            # Need to patch os.path to force file to not exist
            with patch("quantscraper.utils.os.path") as mock_path:
                mock_path.isfile = Mock(return_value=False)
                with self.assertRaises(utils.DataSavingError):
                    utils.save_plaintext(dummy_text, "path/to/fn.txt")


class TestLoadHTMLTemplate(unittest.TestCase):
    # Template() parses any string, which is what file.read() returns,
    # so can't test that the template is correctly formatted here

    # Tests that utils.load_html_tempate() can load file
    def test_success(self):
        m = mock_open(read_data="foo")

        # Save file to specified folder with filename template:
        with patch("quantscraper.utils.open", m):

            res = utils.load_html_template("path/to/fn.txt")
            # Check calls are as expected
            m.assert_called_once_with("path/to/fn.txt", "r")
            # Assert return value is a template and has the appropriate value
            self.assertIsInstance(res, string.Template)
            self.assertEqual(res.substitute(), "foo")

    def test_success_with_placeholder(self):
        m = mock_open(read_data="foo = $value")

        # Save file to specified folder with filename template:
        with patch("quantscraper.utils.open", m):

            res = utils.load_html_template("path/to/fn.txt")
            # Check calls are as expected
            m.assert_called_once_with("path/to/fn.txt", "r")
            # Assert return value is a template and has the appropriate value
            self.assertIsInstance(res, string.Template)
            self.assertEqual(res.substitute(value=5), "foo = 5")

    def test_file_doesnt_exist(self):
        # Check that the DataReadingError is raised when file doesn't exist
        m = mock_open()
        m.side_effect = FileNotFoundError("")
        with patch("quantscraper.utils.open", m):
            with self.assertRaises(utils.DataReadingError):
                utils.load_html_template("path/to/fn.txt")

    def test_io_error(self):
        # Check that the DataReadingError is raised when generic IOError is
        # encountered
        m = mock_open()
        m.side_effect = IOError("")
        with patch("quantscraper.utils.open", m):
            with self.assertRaises(utils.DataReadingError):
                utils.load_html_template("path/to/fn.txt")


class TestLoadDeviceConfiguration(unittest.TestCase):
    # Unfortunately can't mock JSONDecodeError to assert this error is handled
    # correctly, as the error needs to be instantiated which I can't mock.
    # However, I have tested this functionality through running the program
    # with invalid JSON files

    def test_success(self):
        m = mock_open(read_data="foo")

        with patch("quantscraper.utils.DEVICES_FN", "foo.json"):
            with patch("quantscraper.utils.open", m):
                with patch("quantscraper.utils.json") as mock_json:
                    mock_ret = Mock()
                    mock_load = Mock(return_value=mock_ret)
                    mock_json.load = mock_load

                    res = utils.load_device_configuration()

                    # Check calls are as expected
                    m.assert_called_once_with("foo.json", "r")
                    mock_load.assert_called_once_with(m())
                    self.assertEqual(res, mock_ret)

    def test_file_not_found(self):
        # If file isn't present then should raise an error
        m = mock_open()
        m.side_effect = FileNotFoundError()

        with patch("quantscraper.utils.DEVICES_FN", "foo.json"):
            with patch("quantscraper.utils.open", m):
                with patch("quantscraper.utils.json") as mock_json:
                    mock_ret = Mock()
                    mock_load = Mock(return_value=mock_ret)
                    mock_json.load = mock_load

                    with self.assertRaises(utils.SetupError):
                        utils.load_device_configuration()


if __name__ == "__main__":
    unittest.main()
