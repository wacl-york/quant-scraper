"""
    test_connect.py
    ~~~~~~~~~~~~~~~

    Unit tests for Manufacturer.connect() methods.
"""

import unittest
import configparser
from unittest.mock import patch, MagicMock, Mock
from requests.exceptions import Timeout, HTTPError
import quantscraper.manufacturers.Aeroqual as Aeroqual
import quantscraper.manufacturers.AQMesh as AQMesh
import quantscraper.manufacturers.Zephyr as Zephyr
import quantscraper.manufacturers.MyQuantAQ as MyQuantAQ
from quantscraper.utils import LoginError

# TODO Are these unit tests sufficient? Just test that error is thrown for
# specific HTTP error codes.
# Add dummy authentication problems and test for them


class TestAeroqual(unittest.TestCase):

    # TODO Should config be mocked too, or is it fair enough to use the example
    # config that is bundled with the source code?
    cfg = configparser.ConfigParser()
    cfg.read("example.ini")
    aeroqual = Aeroqual.Aeroqual(cfg)

    def _mock_response(
        self,
        status=200,
        content="CONTENT",
        json_data=None,
        raise_for_status=None,
        text=None,
    ):
        """
           Helper function to build mock response. Taken from:
           https://gist.github.com/evansde77/45467f5a7af84d2a2d34f3fcb357449c
           """
        mock_resp = Mock()
        # mock raise_for_status call w/optional error
        if raise_for_status is not None:
            mock_resp.raise_for_status = Mock()
            mock_resp.raise_for_status.side_effect = raise_for_status
        # set status code and content
        mock_resp.status_code = status
        mock_resp.content = content
        mock_resp.text = text
        # add json data if provided
        if json_data is not None:
            mock_resp.json = Mock(return_value=json_data)
        mock_post = Mock(post=Mock(return_value=mock_resp))
        return mock_post

    # Mock a status code return of 200
    def test_success(self):
        resp = self._mock_response(text="Foo")
        with patch("quantscraper.manufacturers.Aeroqual.re.Session") as mock_session:
            mock_session.return_value = resp
            try:
                self.aeroqual.connect()
            except:
                self.fail("Connect raised exception with status code 200")

    # Should definitely be able to DRY these HTTP errors once have more
    # familiarity with mock library.
    # It is useful to separate them so that can test custom error messages

    # Bad request
    def test_400(self):
        resp = self._mock_response(status=400, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.Aeroqual.re.Session") as mock_session:
            mock_session.return_value = resp
            with self.assertRaises(HTTPError):
                res = self.aeroqual.connect()

    # Unauthorised
    def test_401(self):
        resp = self._mock_response(status=401, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.Aeroqual.re.Session") as mock_session:
            mock_session.return_value = resp
            with self.assertRaises(HTTPError):
                res = self.aeroqual.connect()

    # Forbidden
    def test_403(self):
        resp = self._mock_response(status=403, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.Aeroqual.re.Session") as mock_session:
            mock_session.return_value = resp
            with self.assertRaises(HTTPError):
                res = self.aeroqual.connect()

    # Not found
    def test_404(self):
        resp = self._mock_response(status=404, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.Aeroqual.re.Session") as mock_session:
            mock_session.return_value = resp
            with self.assertRaises(HTTPError):
                res = self.aeroqual.connect()

    # timeout
    def test_408(self):
        resp = self._mock_response(status=401, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.Aeroqual.re.Session") as mock_session:
            mock_session.return_value = resp
            with self.assertRaises(HTTPError):
                res = self.aeroqual.connect()

    def test_login_failure(self):
        cfg2 = configparser.ConfigParser()
        cfg2.read("example.ini")
        cfg2.set("Aeroqual", "Username", "foo")
        cfg2.set("Aeroqual", "Password", "foo")
        aeroqual = Aeroqual.Aeroqual(cfg2)
        with self.assertRaises(LoginError):
            aeroqual.connect()


class TestAQMesh(unittest.TestCase):

    # TODO Should config be mocked too, or is it fair enough to use the example
    # config that is bundled with the source code?
    cfg = configparser.ConfigParser()
    cfg.read("example.ini")
    aqmesh = AQMesh.AQMesh(cfg)

    def _mock_response(
        self,
        status=200,
        content="CONTENT",
        json_data=None,
        raise_for_status=None,
        text=None,
    ):
        """
           Helper function to build mock response. Taken from:
           https://gist.github.com/evansde77/45467f5a7af84d2a2d34f3fcb357449c
           """
        mock_resp = Mock()
        # mock raise_for_status call w/optional error
        if raise_for_status is not None:
            mock_resp.raise_for_status = Mock()
            mock_resp.raise_for_status.side_effect = raise_for_status
        # set status code and content
        mock_resp.status_code = status
        mock_resp.content = content
        mock_resp.text = text
        # add json data if provided
        if json_data is not None:
            mock_resp.json = Mock(return_value=json_data)
        mock_post = Mock(post=Mock(return_value=mock_resp))
        return mock_post

    # Mock a status code return of 200
    def test_success(self):
        resp = self._mock_response(text="foo")
        with patch("quantscraper.manufacturers.AQMesh.re.Session") as mock_session:
            mock_session.return_value = resp
            try:
                self.aqmesh.connect()
            except:
                self.fail("Connect raised exception with status code 200")

    # Should definitely be able to DRY these HTTP errors once have more
    # familiarity with mock library.
    # It is useful to separate them so that can test custom error messages

    # Bad request
    def test_400(self):
        resp = self._mock_response(status=400, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.AQMesh.re.Session") as mock_session:
            mock_session.return_value = resp
            with self.assertRaises(HTTPError):
                res = self.aqmesh.connect()

    # Unauthorised
    def test_401(self):
        resp = self._mock_response(status=401, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.AQMesh.re.Session") as mock_session:
            mock_session.return_value = resp
            with self.assertRaises(HTTPError):
                res = self.aqmesh.connect()

    # Forbidden
    def test_403(self):
        resp = self._mock_response(status=403, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.AQMesh.re.Session") as mock_session:
            mock_session.return_value = resp
            with self.assertRaises(HTTPError):
                res = self.aqmesh.connect()

    # Not found
    def test_404(self):
        resp = self._mock_response(status=404, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.AQMesh.re.Session") as mock_session:
            mock_session.return_value = resp
            with self.assertRaises(HTTPError):
                res = self.aqmesh.connect()

    # timeout
    def test_408(self):
        resp = self._mock_response(status=401, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.AQMesh.re.Session") as mock_session:
            mock_session.return_value = resp
            with self.assertRaises(HTTPError):
                res = self.aqmesh.connect()

    def test_login_failure(self):
        cfg2 = configparser.ConfigParser()
        cfg2.read("example.ini")
        cfg2.set("AQMesh", "Username", "foo")
        cfg2.set("AQMesh", "Password", "foo")
        aqmesh = AQMesh.AQMesh(cfg2)
        with self.assertRaises(LoginError):
            aqmesh.connect()


class TestZephyr(unittest.TestCase):

    # Ideally would test for authentication issues, but the Zephyr API returns
    # an access token no matter what username/password combination is provided,
    # so credential errors are only identified downstream when attempting to
    # pull data using the generated access token.

    # TODO Should config be mocked too, or is it fair enough to use the example
    # config that is bundled with the source code?
    cfg = configparser.ConfigParser()
    cfg.read("example.ini")

    def _mock_response(
        self,
        status=200,
        content="CONTENT",
        json_data=None,
        raise_for_status=None,
        text=None,
    ):
        """
           Helper function to build mock response. Taken from:
           https://gist.github.com/evansde77/45467f5a7af84d2a2d34f3fcb357449c
           """
        zephyr = Zephyr.Zephyr(self.cfg)
        mock_resp = Mock()
        # mock raise_for_status call w/optional error
        if raise_for_status is not None:
            mock_resp.raise_for_status = Mock()
            mock_resp.raise_for_status.side_effect = raise_for_status
        # set status code and content
        mock_resp.status_code = status
        mock_resp.content = content
        mock_resp.text = text
        # add json data if provided
        if json_data is not None:
            mock_resp.json = Mock(return_value=json_data)
        mock_post = Mock(post=Mock(return_value=mock_resp))
        return mock_post

    # Mock a status code return of 200
    def test_success(self):
        zephyr = Zephyr.Zephyr(self.cfg)
        resp = self._mock_response(json_data={"access_token": "foo"}, text="foo")
        with patch("quantscraper.manufacturers.Zephyr.re.Session") as mock_session:
            mock_session.return_value = resp
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
        resp = self._mock_response(status=400, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.Zephyr.re.Session") as mock_session:
            mock_session.return_value = resp
            with self.assertRaises(HTTPError):
                res = zephyr.connect()
            self.assertIsNone(zephyr.api_token)

    # Unauthorised
    def test_401(self):
        zephyr = Zephyr.Zephyr(self.cfg)
        resp = self._mock_response(status=401, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.Zephyr.re.Session") as mock_session:
            mock_session.return_value = resp
            with self.assertRaises(HTTPError):
                res = zephyr.connect()
            self.assertIsNone(zephyr.api_token)

    # Forbidden
    def test_403(self):
        zephyr = Zephyr.Zephyr(self.cfg)
        resp = self._mock_response(status=403, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.Zephyr.re.Session") as mock_session:
            mock_session.return_value = resp
            with self.assertRaises(HTTPError):
                res = zephyr.connect()
            self.assertIsNone(zephyr.api_token)

    # Not found
    def test_404(self):
        zephyr = Zephyr.Zephyr(self.cfg)
        resp = self._mock_response(status=404, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.Zephyr.re.Session") as mock_session:
            mock_session.return_value = resp
            with self.assertRaises(HTTPError):
                res = zephyr.connect()
            self.assertIsNone(zephyr.api_token)

    # timeout
    def test_408(self):
        zephyr = Zephyr.Zephyr(self.cfg)
        resp = self._mock_response(status=401, raise_for_status=HTTPError(""))

        with patch("quantscraper.manufacturers.Zephyr.re.Session") as mock_session:
            mock_session.return_value = resp
            with self.assertRaises(HTTPError):
                res = zephyr.connect()
            self.assertIsNone(zephyr.api_token)


class TestMyQuantAQ(unittest.TestCase):
    # Cannot test HTTP errors as quantaq API should do this for us
    # Could pass in fake API token and check that error raised... can't really
    # test opposite can I? I.e. is it safe/appropriate to pass in correct
    # token and test that it is logged in correctly?

    def test_error_incorrect_token(self):

        cfg = configparser.ConfigParser()
        cfg.read("example.ini")
        cfg.set("QuantAQ", "api_token", "foo")
        myquantaq = MyQuantAQ.MyQuantAQ(cfg)
        with self.assertRaises(LoginError):
            res = myquantaq.connect()


# TODO Test only called once
if __name__ == "__main__":
    unittest.main()
