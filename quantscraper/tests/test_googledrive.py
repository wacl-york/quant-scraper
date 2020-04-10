"""
    test_googledrive.py
    ~~~~~~~~~~~~~~~~~~~

    Unit tests for functions that use the Google Drive API.
"""

import unittest
import socket
import configparser
from unittest.mock import patch, MagicMock, Mock, call
import quantscraper.utils as utils
import quantscraper.cli as cli
from googleapiclient.errors import HttpError
from quantscraper.tests.test_utils import build_mock_response

class TestAuthGoogleAPI(unittest.TestCase):
    # the utils.auth_google_api method should return a connection to Google
    # Drive's API

    def test_no_credentials_file(self):
        with patch("quantscraper.utils.service_account.Credentials.from_service_account_file") as mock_cred_obj:
            mock_cred_obj.side_effect = FileNotFoundError("")
            with self.assertRaises(utils.GoogleAPIError):
                utils.auth_google_api("imaginary_file.txt")

    def test_file_format_error(self):
        with patch("quantscraper.utils.service_account.Credentials.from_service_account_file") as mock_cred_obj:
            mock_cred_obj.side_effect = ValueError("")
            with self.assertRaises(utils.GoogleAPIError):
                utils.auth_google_api("imaginary_file.txt")

    def test_success(self):
        # Patch credentials call
        with patch("quantscraper.utils.service_account.Credentials.from_service_account_file") as mock_cred_obj:
            mock_credentials = Mock()
            mock_cred_obj.return_value = mock_credentials

            # Patch service builder
            with patch("quantscraper.utils.googleapiclient.discovery.build") as mock_build:
                mock_service = Mock()
                mock_build.return_value = mock_service

                service = utils.auth_google_api("imaginary_file.txt")
                
                # Using standard recommended google drive scope
                exp_scopes = ["https://www.googleapis.com/auth/drive.file"]

                # Test calls
                mock_cred_obj.assert_called_once_with("imaginary_file.txt",
                                                      scopes=exp_scopes)
                mock_build.assert_called_once_with('drive', 'v3', 
                                                   credentials=mock_credentials,
                                                   cache_discovery=False)
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
            mock_create = Mock(return_value = Mock(execute=mock_execute))
            mock_files = Mock(return_value = Mock(create=mock_create))
            mock_service = Mock(files=mock_files)

            utils.upload_file_google_drive(mock_service,
                                           "drive1/drive2/foo.txt",
                                           "123foo",
                                           "text/foobar")

            # Test calls are as expected
            mock_mediafile.assert_called_once_with("drive1/drive2/foo.txt",
                                                   mimetype="text/foobar")
            mock_create.assert_called_once_with(body={'name': 'foo.txt',
                                                      'mimeType': 'text/foobar',
                                                      'parents': ['123foo']
                                                     },
                                                media_body=mock_media,
                                                supportsAllDrives=True)

    def test_httperror(self):
        with patch("quantscraper.utils.MediaFileUpload") as mock_mediafile:
            #with patch("quantscraper.utils.HttpError") as mock_httperror:
            mock_media = Mock()
            mock_mediafile.return_value = mock_media

            # Setup the services.files().create().execute() mock pipeline
            mock_resp = build_mock_response(status=400)
            mock_execute = Mock(side_effect=HttpError(mock_resp, b""))
            mock_create = Mock(return_value = Mock(execute=mock_execute))
            mock_files = Mock(return_value = Mock(create=mock_create))
            mock_service = Mock(files=mock_files)

            with self.assertRaises(utils.DataUploadError):
                utils.upload_file_google_drive(mock_service,
                                               "drive1/drive2/foo.txt",
                                               "123foo",
                                               "text/foobar")


class TestUploadDataGoogleDrive(unittest.TestCase):
    # the cli.upload_data_googledrive function uploads a list of files
    # with the same mime_type to Google Drive

    def test_success(self):
        with patch("quantscraper.cli.utils.upload_file_google_drive") as mock_upload:
            mock_service = Mock()
            fns = ['1.txt', '2.txt', '3.txt']
            folder_id = 'FoOBaR'
            mime_type = 'text/foobar'
            exp_calls = [call(mock_service, fn, folder_id, mime_type) for fn in fns]

            cli.upload_data_googledrive(mock_service,
                                        fns,
                                        folder_id,
                                        mime_type)

            calls = mock_upload.mock_calls

            self.assertEqual(calls, exp_calls)

    def test_empty_list(self):
        with patch("quantscraper.cli.utils.upload_file_google_drive") as mock_upload:
            mock_service = Mock()
            fns = []
            folder_id = 'FoOBaR'
            mime_type = 'text/foobar'
            exp_calls = []

            cli.upload_data_googledrive(mock_service,
                                        fns,
                                        folder_id,
                                        mime_type)

            calls = mock_upload.mock_calls

            self.assertEqual(calls, exp_calls)

    def test_fns_None(self):
        with patch("quantscraper.cli.utils.upload_file_google_drive") as mock_upload:
            mock_service = Mock()
            fns = None
            folder_id = 'FoOBaR'
            mime_type = 'text/foobar'
            exp_calls = []

            cli.upload_data_googledrive(mock_service,
                                        fns,
                                        folder_id,
                                        mime_type)

            calls = mock_upload.mock_calls

            self.assertEqual(calls, exp_calls)


if __name__ == "__main__":
    unittest.main()
