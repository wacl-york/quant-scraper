"""
    test_connect.py
    ~~~~~~~~~~~~~~~

    Unit tests for Manufacturer.connect() methods.
"""

import os
import unittest
from collections import defaultdict
from unittest.mock import patch, Mock, MagicMock
from requests.exceptions import HTTPError
from quantaq.baseapi import DataReadError
import quantscraper.manufacturers.Aeroqual as Aeroqual
import quantscraper.manufacturers.AQMesh as AQMesh
import quantscraper.manufacturers.Zephyr as Zephyr
import quantscraper.manufacturers.MyQuantAQ as MyQuantAQ
from quantscraper.utils import LoginError
from test_utils import build_mock_response

# Setup dummy env variables
os.environ["AEROQUAL_USER"] = "foo"
os.environ["AEROQUAL_PW"] = "foo"
os.environ["AQMESH_USER"] = "foo"
os.environ["AQMESH_PW"] = "foo"
os.environ["ZEPHYR_USER"] = "foo"
os.environ["ZEPHYR_PW"] = "foo"
os.environ["QUANTAQ_API_TOKEN"] = "foo"


class TestAeroqual(unittest.TestCase):
    start_dt = MagicMock()
    end_dt = MagicMock()
    cfg = defaultdict(str)
    fields = []
    aeroqual = Aeroqual.Aeroqual(start_dt, end_dt, cfg, fields)

    # Mock a status code return of 200
    def test_success(self):
        resp = build_mock_response(text="Foo")
        post_mock = Mock(return_value=resp)
        with patch("quantscraper.manufacturers.Aeroqual.re.Session") as mock_session:
            mock_session.return_value = Mock(post=post_mock)
            try:
                self.aeroqual.connect()
                post_mock.assert_called_once_with(
                    self.aeroqual.auth_url,
                    data=self.aeroqual.auth_params,
                    headers=self.aeroqual.auth_headers,
                )
            except:
                self.fail("Connect raised exception with status code 200")

    # Should definitely be able to DRY these HTTP errors once have more
    # familiarity with mock library.
    # It is useful to separate them so that can test custom error messages

    # Bad request
    def test_400(self):
        resp = build_mock_response(status=400, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.Aeroqual.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                self.aeroqual.connect()

    # Unauthorised
    def test_401(self):
        resp = build_mock_response(status=401, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.Aeroqual.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                self.aeroqual.connect()

    # Forbidden
    def test_403(self):
        resp = build_mock_response(status=403, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.Aeroqual.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                self.aeroqual.connect()

    # Not found
    def test_404(self):
        resp = build_mock_response(status=404, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.Aeroqual.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                self.aeroqual.connect()

    # timeout
    def test_408(self):
        resp = build_mock_response(status=401, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.Aeroqual.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                self.aeroqual.connect()


class TestAQMesh(unittest.TestCase):
    start_dt = MagicMock()
    end_dt = MagicMock()
    cfg = defaultdict(str)
    fields = []
    aqmesh = AQMesh.AQMesh(start_dt, end_dt, cfg, fields)

    # Mock a status code return of 200
    def test_success(self):
        resp = build_mock_response(text="foo")
        post_mock = Mock(return_value=resp)
        with patch("quantscraper.manufacturers.AQMesh.re.Session") as mock_session:
            mock_session.return_value = Mock(post=post_mock)
            try:
                self.aqmesh.connect()
                post_mock.assert_called_once_with(
                    self.aqmesh.auth_url,
                    data=self.aqmesh.auth_params,
                    headers=self.aqmesh.auth_headers,
                )
            except:
                self.fail("Connect raised exception with status code 200")

    # Should definitely be able to DRY these HTTP errors once have more
    # familiarity with mock library.
    # It is useful to separate them so that can test custom error messages

    # Bad request
    def test_400(self):
        resp = build_mock_response(status=400, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.AQMesh.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                self.aqmesh.connect()

    # Unauthorised
    def test_401(self):
        resp = build_mock_response(status=401, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.AQMesh.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                self.aqmesh.connect()

    # Forbidden
    def test_403(self):
        resp = build_mock_response(status=403, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.AQMesh.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                self.aqmesh.connect()

    # Not found
    def test_404(self):
        resp = build_mock_response(status=404, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.AQMesh.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                self.aqmesh.connect()

    # timeout
    def test_408(self):
        resp = build_mock_response(status=401, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.AQMesh.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                self.aqmesh.connect()


class TestZephyr(unittest.TestCase):
    # Ideally would test for authentication issues, but the Zephyr API returns
    # an access token no matter what username/password combination is provided,
    # so credential errors are only identified downstream when attempting to
    # pull data using the generated access token.

    start_dt = MagicMock()
    end_dt = MagicMock()
    cfg = defaultdict(str)
    fields = []
    zephyr = Zephyr.Zephyr(start_dt, end_dt, cfg, fields)

    # Mock a status code return of 200
    def test_success(self):
        resp = build_mock_response(json_data={"access_token": "foo"}, text="foo")
        post_mock = Mock(return_value=resp)
        with patch("quantscraper.manufacturers.Zephyr.re.Session") as mock_session:
            mock_session.return_value = Mock(post=post_mock)
            try:
                self.zephyr.connect()
                self.assertEqual(self.zephyr.api_token, "foo")
                post_mock.assert_called_once_with(
                    self.zephyr.auth_url,
                    data=self.zephyr.auth_params,
                    headers=self.zephyr.auth_headers,
                )
            except:
                self.fail("Connect raised exception with status code 200")

    # Should definitely be able to DRY these HTTP errors once have more
    # familiarity with mock library.
    # It is useful to separate them so that can test custom error messages

    # Bad request
    def test_400(self):
        resp = build_mock_response(status=400, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.Zephyr.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                self.zephyr.connect()
            self.assertIsNone(self.zephyr.api_token)

    # Unauthorised
    def test_401(self):
        resp = build_mock_response(status=401, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.Zephyr.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                self.zephyr.connect()
            self.assertIsNone(self.zephyr.api_token)

    # Forbidden
    def test_403(self):
        resp = build_mock_response(status=403, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.Zephyr.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                self.zephyr.connect()
            self.assertIsNone(self.zephyr.api_token)

    # Not found
    def test_404(self):
        resp = build_mock_response(status=404, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.Zephyr.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                self.zephyr.connect()
            self.assertIsNone(self.zephyr.api_token)

    # timeout
    def test_408(self):
        resp = build_mock_response(status=401, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.Zephyr.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                self.zephyr.connect()
            self.assertIsNone(self.zephyr.api_token)


class TestMyQuantAQ(unittest.TestCase):
    # Cannot test HTTP errors as quantaq API should do this for us
    # Don't want to do any actual IO, so instead will just mock the
    # quantaq.get_account() method raising an error, an indication that the
    # login has failed
    start_dt = MagicMock()
    end_dt = MagicMock()
    cfg = defaultdict(str)
    fields = []
    myquantaq = MyQuantAQ.MyQuantAQ(start_dt, end_dt, cfg, fields)

    def test_success(self):
        # mock the get_account method that is called to test authentication
        get_account_mock = Mock(return_value="foo", side_effect=None)
        with patch("quantscraper.manufacturers.MyQuantAQ.quantaq.QuantAQ") as mock_api:
            # Ensure the patched Class returns a Mock instance
            mock_api.return_value = Mock(get_account=get_account_mock)
            try:
                self.myquantaq.connect()
                get_account_mock.assert_called_once()
            except:
                self.fail("Error during supposedly successful connection.")

    def test_login_failure(self):
        # give mock api a mock return value, that raises DataReadError when
        # .get_account() is called
        get_account_mock = Mock(side_effect=DataReadError)
        with patch("quantscraper.manufacturers.MyQuantAQ.quantaq.QuantAQ") as mock_api:
            mock_api.return_value = Mock(get_account=get_account_mock)
            with self.assertRaises(LoginError):
                self.myquantaq.connect()
                get_account_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
