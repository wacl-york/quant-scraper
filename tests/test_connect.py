"""
    test_connect.py
    ~~~~~~~~~~~~~~~

    Unit tests for Manufacturer.connect() methods.
"""

import os
import unittest
from collections import defaultdict
from unittest.mock import patch, Mock
from requests.exceptions import HTTPError
from quantaq.baseapi import DataReadError
import quantscraper.manufacturers.Aeroqual as Aeroqual
import quantscraper.manufacturers.AQMesh as AQMesh
import quantscraper.manufacturers.Zephyr as Zephyr
import quantscraper.manufacturers.MyQuantAQ as MyQuantAQ
import quantscraper.manufacturers.AURN as AURN
import quantscraper.manufacturers.PurpleAir as PurpleAir
from quantscraper.utils import LoginError
from test_utils import build_mock_response

# Setup dummy env variables
os.environ["AEROQUAL_USER"] = "foo"
os.environ["AEROQUAL_PW"] = "foo"
os.environ["AQMESH_API_ID"] = "myid"
os.environ["AQMESH_API_TOKEN"] = "mytoken"
os.environ["ZEPHYR_USER"] = "foo"
os.environ["ZEPHYR_PW"] = "foo"
os.environ["QUANTAQ_API_TOKEN"] = "foo"


class TestAeroqual(unittest.TestCase):
    cfg = defaultdict(str)
    fields = []
    aeroqual = Aeroqual.Aeroqual(cfg, fields)

    # Mock a status code return of 200
    def test_success(self):
        resp = build_mock_response(text="Foo")
        post_mock = Mock(return_value=resp)
        with patch("quantscraper.manufacturers.Aeroqual.re.Session") as mock_session:
            mock_session.return_value = Mock(post=post_mock)
            self.aeroqual.connect()
            post_mock.assert_called_once_with(
                self.aeroqual.auth_url,
                data=self.aeroqual.auth_params,
                headers=self.aeroqual.auth_headers,
            )

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
    cfg = defaultdict(str)
    fields = []
    aqmesh = AQMesh.AQMesh(cfg, fields)

    # Mock a status code return of 200
    def test_success(self):
        resp = build_mock_response(text="foo")
        get_mock = Mock(return_value=resp)
        with patch("quantscraper.manufacturers.AQMesh.re.Session") as mock_session:
            mock_session.return_value = Mock(get=get_mock)

            self.aqmesh.connect()
            get_mock.assert_called_once_with(
                "https://api.airmonitors.net/3.5/GET/myid/mytoken/stations"
            )

    # Should definitely be able to DRY these HTTP errors once have more
    # familiarity with mock library.
    # It is useful to separate them so that can test custom error messages

    # No HTTP error but incorrect credentials
    def test_incorrect_creds(self):
        resp = build_mock_response(text="AUTHENTICATION FAILED")
        get_mock = Mock(return_value=resp)
        with patch("quantscraper.manufacturers.AQMesh.re.Session") as mock_session:
            mock_session.return_value = Mock(get=get_mock)
            with self.assertRaises(LoginError):
                self.aqmesh.connect()

    # Bad request
    def test_400(self):
        resp = build_mock_response(status=400, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.AQMesh.re.Session") as mock_session:
            mock_session.return_value = Mock(get=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                self.aqmesh.connect()

    # Unauthorised
    def test_401(self):
        resp = build_mock_response(status=401, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.AQMesh.re.Session") as mock_session:
            mock_session.return_value = Mock(get=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                self.aqmesh.connect()

    # Forbidden
    def test_403(self):
        resp = build_mock_response(status=403, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.AQMesh.re.Session") as mock_session:
            mock_session.return_value = Mock(get=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                self.aqmesh.connect()

    # Not found
    def test_404(self):
        resp = build_mock_response(status=404, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.AQMesh.re.Session") as mock_session:
            mock_session.return_value = Mock(get=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                self.aqmesh.connect()

    # timeout
    def test_408(self):
        resp = build_mock_response(status=401, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.AQMesh.re.Session") as mock_session:
            mock_session.return_value = Mock(get=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                self.aqmesh.connect()


class TestZephyr(unittest.TestCase):
    # Ideally would test for authentication issues, but the Zephyr API returns
    # an access token no matter what username/password combination is provided,
    # so credential errors are only identified downstream when attempting to
    # pull data using the generated access token.

    cfg = defaultdict(str)
    fields = []
    zephyr = Zephyr.Zephyr(cfg, fields)

    # Mock a status code return of 200
    def test_success(self):
        resp = build_mock_response(json_data={"access_token": "foo"}, text="foo")
        post_mock = Mock(return_value=resp)
        with patch("quantscraper.manufacturers.Zephyr.re.Session") as mock_session:
            mock_session.return_value = Mock(post=post_mock)
            self.zephyr.connect()
            self.assertEqual(self.zephyr.api_token, "foo")
            post_mock.assert_called_once_with(
                self.zephyr.auth_url,
                data=self.zephyr.auth_params,
                headers=self.zephyr.auth_headers,
            )

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
    cfg = defaultdict(str)
    fields = []
    myquantaq = MyQuantAQ.MyQuantAQ(cfg, fields)

    def test_success(self):
        # mock the get_account method that is called to test authentication
        get_account_mock = Mock(return_value="foo", side_effect=None)
        with patch("quantscraper.manufacturers.MyQuantAQ.quantaq.QuantAQ") as mock_api:
            # Ensure the patched Class returns a Mock instance
            mock_api.return_value = Mock(get_account=get_account_mock)
            self.myquantaq.connect()
            get_account_mock.assert_called_once()

    def test_login_failure(self):
        # give mock api a mock return value, that raises DataReadError when
        # .get_account() is called
        get_account_mock = Mock(side_effect=DataReadError)
        with patch("quantscraper.manufacturers.MyQuantAQ.quantaq.QuantAQ") as mock_api:
            mock_api.return_value = Mock(get_account=get_account_mock)
            with self.assertRaises(LoginError):
                self.myquantaq.connect()
                get_account_mock.assert_called_once()


class TestAURN(unittest.TestCase):
    # AURN doesn't do anything in the connect() method except instantiate a
    # Session.
    cfg = defaultdict(str)
    fields = []
    myaurn = AURN.AURN(cfg, fields)

    def test_success(self):
        # mock the get_account method that is called to test authentication
        session = Mock(return_value="foo", side_effect=None)
        with patch("quantscraper.manufacturers.AURN.re") as mock_re:
            mock_sesh = Mock(return_value="5")
            mock_re.Session = mock_sesh
            self.myaurn.connect()
            mock_sesh.assert_called_once()
            self.assertEqual(self.myaurn.session, "5")


class TestPurpleAir(unittest.TestCase):
    # PurpleAir hasn't implemented a connect method yet
    cfg = defaultdict(str)
    fields = []
    mypa = PurpleAir.PurpleAir(cfg, fields)

    def test_success(self):
        res = self.mypa.connect()
        self.assertEqual(res, None)


if __name__ == "__main__":
    unittest.main()
