"""
    test_connect.py
    ~~~~~~~~~~~~~~~

    Unit tests for Manufacturer.connect() methods.
"""

import unittest
import configparser
from unittest.mock import patch, Mock
from requests.exceptions import HTTPError
from quantaq.baseapi import DataReadError
import quantscraper.manufacturers.Aeroqual as Aeroqual
import quantscraper.manufacturers.AQMesh as AQMesh
import quantscraper.manufacturers.Zephyr as Zephyr
import quantscraper.manufacturers.MyQuantAQ as MyQuantAQ
from quantscraper.utils import LoginError
from quantscraper.tests.test_utils import build_mock_response

# TODO Are these unit tests sufficient? Just test that error is thrown for
# specific HTTP error codes and that login attempts with incorrect credentials
# will fail.
# Haven't checked for login with correct credentials, but would that be a
# security risk?

# TODO Should config be mocked too, or is it fair enough to use the example
# config that is bundled with the source code?


class TestAeroqual(unittest.TestCase):
    cfg = configparser.ConfigParser()
    cfg.read("example.ini")
    aeroqual = Aeroqual.Aeroqual(cfg)

    # Mock a status code return of 200
    def test_success(self):
        resp = build_mock_response(text="Foo")
        with patch("quantscraper.manufacturers.Aeroqual.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            try:
                self.aeroqual.connect()
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
                res = self.aeroqual.connect()

    # Unauthorised
    def test_401(self):
        resp = build_mock_response(status=401, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.Aeroqual.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                res = self.aeroqual.connect()

    # Forbidden
    def test_403(self):
        resp = build_mock_response(status=403, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.Aeroqual.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                res = self.aeroqual.connect()

    # Not found
    def test_404(self):
        resp = build_mock_response(status=404, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.Aeroqual.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                res = self.aeroqual.connect()

    # timeout
    def test_408(self):
        resp = build_mock_response(status=401, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.Aeroqual.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                res = self.aeroqual.connect()


class TestAQMesh(unittest.TestCase):
    cfg = configparser.ConfigParser()
    cfg.read("example.ini")
    aqmesh = AQMesh.AQMesh(cfg)

    # Mock a status code return of 200
    def test_success(self):
        resp = build_mock_response(text="foo")
        with patch("quantscraper.manufacturers.AQMesh.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            try:
                self.aqmesh.connect()
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
                res = self.aqmesh.connect()

    # Unauthorised
    def test_401(self):
        resp = build_mock_response(status=401, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.AQMesh.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                res = self.aqmesh.connect()

    # Forbidden
    def test_403(self):
        resp = build_mock_response(status=403, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.AQMesh.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                res = self.aqmesh.connect()

    # Not found
    def test_404(self):
        resp = build_mock_response(status=404, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.AQMesh.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                res = self.aqmesh.connect()

    # timeout
    def test_408(self):
        resp = build_mock_response(status=401, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.AQMesh.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                res = self.aqmesh.connect()


class TestZephyr(unittest.TestCase):
    # Ideally would test for authentication issues, but the Zephyr API returns
    # an access token no matter what username/password combination is provided,
    # so credential errors are only identified downstream when attempting to
    # pull data using the generated access token.

    cfg = configparser.ConfigParser()
    cfg.read("example.ini")

    # Mock a status code return of 200
    def test_success(self):
        zephyr = Zephyr.Zephyr(self.cfg)
        resp = build_mock_response(json_data={"access_token": "foo"}, text="foo")
        with patch("quantscraper.manufacturers.Zephyr.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            try:
                zephyr.connect()
            except:
                self.fail("Connect raised exception with status code 200")
            self.assertEqual(zephyr.api_token, "foo")

    # Should definitely be able to DRY these HTTP errors once have more
    # familiarity with mock library.
    # It is useful to separate them so that can test custom error messages

    # Bad request
    def test_400(self):
        zephyr = Zephyr.Zephyr(self.cfg)
        resp = build_mock_response(status=400, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.Zephyr.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                res = zephyr.connect()
            self.assertIsNone(zephyr.api_token)

    # Unauthorised
    def test_401(self):
        zephyr = Zephyr.Zephyr(self.cfg)
        resp = build_mock_response(status=401, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.Zephyr.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                res = zephyr.connect()
            self.assertIsNone(zephyr.api_token)

    # Forbidden
    def test_403(self):
        zephyr = Zephyr.Zephyr(self.cfg)
        resp = build_mock_response(status=403, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.Zephyr.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                res = zephyr.connect()
            self.assertIsNone(zephyr.api_token)

    # Not found
    def test_404(self):
        zephyr = Zephyr.Zephyr(self.cfg)
        resp = build_mock_response(status=404, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.Zephyr.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                res = zephyr.connect()
            self.assertIsNone(zephyr.api_token)

    # timeout
    def test_408(self):
        zephyr = Zephyr.Zephyr(self.cfg)
        resp = build_mock_response(status=401, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.Zephyr.re.Session") as mock_session:
            mock_session.return_value = Mock(post=Mock(return_value=resp))
            with self.assertRaises(LoginError):
                res = zephyr.connect()
            self.assertIsNone(zephyr.api_token)


class TestMyQuantAQ(unittest.TestCase):
    # Cannot test HTTP errors as quantaq API should do this for us
    # Don't want to do any actual IO, so instead will just mock the
    # quantaq.get_account() method raising an error, an indication that the
    # login has failed

    def test_login_failure(self):
        cfg = configparser.ConfigParser()
        cfg.read("example.ini")
        cfg.set("QuantAQ", "api_token", "foo")
        myquantaq = MyQuantAQ.MyQuantAQ(cfg)
        with patch("quantscraper.manufacturers.MyQuantAQ.quantaq.QuantAQ") as mock_api:
            # give mock api a mock return value, that raises DataReadError when
            # .get_account() is called
            mock_instance = Mock(get_account=Mock(side_effect=DataReadError))
            mock_api.return_value = mock_instance
        with self.assertRaises(LoginError):
            res = myquantaq.connect()


# TODO Test only called once
if __name__ == "__main__":
    unittest.main()
