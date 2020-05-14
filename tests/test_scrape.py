"""
    test_scrape.py
    ~~~~~~~~~~~~~~~

    Unit tests for Manufacturer.scrape_device() methods.
"""

import unittest
from collections import defaultdict
from unittest.mock import Mock, MagicMock, call
from datetime import datetime
from requests.exceptions import HTTPError
from quantaq.baseapi import DataReadError
import quantscraper.manufacturers.Aeroqual as Aeroqual
import quantscraper.manufacturers.AQMesh as AQMesh
import quantscraper.manufacturers.Zephyr as Zephyr
import quantscraper.manufacturers.MyQuantAQ as MyQuantAQ
from quantscraper.utils import DataDownloadError
from test_utils import build_mock_response

# Want to test that:
#   - Any HTTP errors are raised
#   - Check that error is raised if data isn't in appropriate format (note, not
#   same as not-having data... or is it?)
#   - Will need client code in CLI to handle raised errors
#   - Will need to move towards having each Device having ownership of its
#   data, and having the .scrape method. So that can run the .scrape() methods
#   from cli.py and in there handle raised errors.
#   Don't want Manufacturer to handle error logging... do we?!


class TestAeroqual(unittest.TestCase):

    # Aeroqual's scrape_device function runs 3 requests:
    #   - post to select device
    #   - post to generate data
    #   - get to download data
    cfg = defaultdict(str)
    fields = []
    aeroqual = Aeroqual.Aeroqual(cfg, fields)

    def test_200_success(self):
        # Mock 200 response on both posts and get
        mock_posts = [build_mock_response(status=200), build_mock_response(status=200)]
        mock_post = Mock(side_effect=mock_posts)
        mock_get = Mock(return_value=build_mock_response(status=200))

        mock_start = datetime(2020, 4, 3, 15, 35, 00)
        mock_end = datetime(2020, 5, 3, 16, 28, 29)

        session_return = Mock(post=mock_post, get=mock_get)
        self.aeroqual.session = session_return
        try:
            self.aeroqual.scrape_device("foo", mock_start, mock_end)
            exp_params = self.aeroqual.data_params.copy()
            exp_params["Period"] = exp_params["Period"].substitute(
                start="04/03/2020", end="05/03/2020"
            )
            exp_post_calls = [
                call(
                    self.aeroqual.select_device_url,
                    json=[self.aeroqual.select_device_string.substitute(device="foo")],
                    headers=self.aeroqual.select_device_headers,
                ),
                call(
                    self.aeroqual.data_url,
                    data=exp_params,
                    headers=self.aeroqual.data_headers,
                ),
            ]
            self.assertEqual(mock_post.mock_calls, exp_post_calls)
            mock_get.assert_called_once_with(
                self.aeroqual.dl_url, headers=self.aeroqual.dl_headers
            )
        except:
            self.fail("Connect raised exception with status code 200")

    def test_retrieves_content(self):
        # Now test that actually download the content we expected
        mock_posts = [build_mock_response(status=200), build_mock_response(status=200)]
        mock_post = Mock(side_effect=mock_posts)
        mock_get = Mock(return_value=build_mock_response(status=200, text="DummyData"))
        mock_start = datetime(2020, 4, 3, 15, 35, 00)
        mock_end = datetime(2020, 5, 3, 16, 28, 29)

        exp_params = self.aeroqual.data_params.copy()
        exp_params["Period"] = exp_params["Period"].substitute(
            start="04/03/2020", end="05/03/2020"
        )

        session_return = Mock(post=mock_post, get=mock_get)
        self.aeroqual.session = session_return
        try:
            resp = self.aeroqual.scrape_device("foo", mock_start, mock_end)
            self.assertEqual(resp, "DummyData")
            exp_post_calls = [
                call(
                    self.aeroqual.select_device_url,
                    json=[self.aeroqual.select_device_string.substitute(device="foo")],
                    headers=self.aeroqual.select_device_headers,
                ),
                call(
                    self.aeroqual.data_url,
                    data=exp_params,
                    headers=self.aeroqual.data_headers,
                ),
            ]
            self.assertEqual(mock_post.mock_calls, exp_post_calls)
            mock_get.assert_called_once_with(
                self.aeroqual.dl_url, headers=self.aeroqual.dl_headers
            )
        except:
            self.fail("Connect raised exception with status code 200")

    def test_select_device_failure_400(self):
        mock_posts = [
            build_mock_response(status=400, raise_for_status=HTTPError()),
            build_mock_response(status=200),
        ]
        mock_get = build_mock_response(status=200)
        mock_start = MagicMock()
        mock_end = MagicMock()
        session_return = Mock(
            post=Mock(side_effect=mock_posts), get=Mock(return_value=mock_get)
        )
        self.aeroqual.session = session_return
        with self.assertRaises(DataDownloadError):
            self.aeroqual.scrape_device("foo", mock_start, mock_end)

    # Don't need to test all non-200 responses, will just do 400 + 404
    def test_select_device_failure_404(self):
        mock_posts = [
            build_mock_response(status=404, raise_for_status=HTTPError()),
            build_mock_response(status=200),
        ]
        mock_get = build_mock_response(status=200)
        session_return = Mock(
            post=Mock(side_effect=mock_posts), get=Mock(return_value=mock_get)
        )
        mock_start = MagicMock()
        mock_end = MagicMock()
        self.aeroqual.session = session_return
        with self.assertRaises(DataDownloadError):
            self.aeroqual.scrape_device("foo", mock_start, mock_end)

    def test_generate_data_failure_400(self):
        mock_posts = [
            build_mock_response(status=200),
            build_mock_response(status=400, raise_for_status=HTTPError()),
        ]
        mock_get = build_mock_response(status=200)
        session_return = Mock(
            post=Mock(side_effect=mock_posts), get=Mock(return_value=mock_get)
        )
        mock_start = MagicMock()
        mock_end = MagicMock()
        self.aeroqual.session = session_return
        with self.assertRaises(DataDownloadError):
            self.aeroqual.scrape_device("foo", mock_start, mock_end)

    def test_generate_data_failure_404(self):
        mock_posts = [
            build_mock_response(status=200),
            build_mock_response(status=404, raise_for_status=HTTPError()),
        ]
        mock_get = build_mock_response(status=200)
        session_return = Mock(
            post=Mock(side_effect=mock_posts), get=Mock(return_value=mock_get)
        )
        mock_start = MagicMock()
        mock_end = MagicMock()
        self.aeroqual.session = session_return
        with self.assertRaises(DataDownloadError):
            self.aeroqual.scrape_device("foo", mock_start, mock_end)

    def test_download_data_failure_400(self):
        mock_posts = [build_mock_response(status=200), build_mock_response(status=200)]
        mock_get = build_mock_response(status=400, raise_for_status=HTTPError())
        session_return = Mock(
            post=Mock(side_effect=mock_posts), get=Mock(return_value=mock_get)
        )
        mock_start = MagicMock()
        mock_end = MagicMock()
        self.aeroqual.session = session_return
        with self.assertRaises(DataDownloadError):
            self.aeroqual.scrape_device("foo", mock_start, mock_end)

    def test_download_data_failure_404(self):
        mock_posts = [build_mock_response(status=200), build_mock_response(status=200)]
        mock_get = build_mock_response(status=400, raise_for_status=HTTPError())
        session_return = Mock(
            post=Mock(side_effect=mock_posts), get=Mock(return_value=mock_get)
        )
        mock_start = MagicMock()
        mock_end = MagicMock()
        self.aeroqual.session = session_return
        with self.assertRaises(DataDownloadError):
            self.aeroqual.scrape_device("foo", mock_start, mock_end)


class TestAQMesh(unittest.TestCase):

    # AQMesh just runs a single GET request to get the data,
    # which is returned in the 'Data' attribute of the resultant JSON
    cfg = defaultdict(str)
    cfg["timezone"] = "+02:00"
    fields = []
    aqmesh = AQMesh.AQMesh(cfg, fields)

    def test_success(self):
        mock_get_resp = build_mock_response(
            status=200, json_data={"Foo": "Bar", "Data": [1, 2, 3]}
        )
        mock_get = Mock(return_value=mock_get_resp)
        session_return = Mock(get=mock_get)
        self.aqmesh.session = session_return

        # Make same substitution with device ID into the GET params and assert
        # that these are used in the function call
        mock_params = self.aqmesh.data_params.copy()
        mock_params["UniqueId"] = mock_params["UniqueId"].substitute(device="123")
        mock_params["Channels"] = mock_params["Channels"].substitute(device="123")
        mock_params["Start"] = mock_params["Start"].substitute(
            start="2020-04-03T15:35:00 +02:00"
        )
        mock_params["End"] = mock_params["End"].substitute(
            end="2020-05-03T16:28:29 +02:00"
        )

        mock_start = datetime(2020, 4, 3, 15, 35, 00)
        mock_end = datetime(2020, 5, 3, 16, 28, 29)
        try:
            res = self.aqmesh.scrape_device("123", mock_start, mock_end)
            self.assertEqual(res, [1, 2, 3])
            mock_get.assert_called_once_with(
                self.aqmesh.data_url,
                headers=self.aqmesh.data_headers,
                params=mock_params,
            )
        except:
            self.fail("Connect raised exception with status code 200")

    # Test that custom DataDownloadError is raised under a variety of failure
    # conditions
    def test_400(self):
        mock_get_resp = build_mock_response(status=400, raise_for_status=HTTPError())
        mock_get = Mock(return_value=mock_get_resp)
        session_return = Mock(get=mock_get)
        self.aqmesh.session = session_return
        mock_start = MagicMock()
        mock_end = MagicMock()

        with self.assertRaises(DataDownloadError):
            self.aqmesh.scrape_device("123", mock_start, mock_end)

    def test_404(self):
        mock_get_resp = build_mock_response(status=404, raise_for_status=HTTPError())
        mock_get = Mock(return_value=mock_get_resp)
        session_return = Mock(get=mock_get)
        self.aqmesh.session = session_return
        mock_start = MagicMock()
        mock_end = MagicMock()

        with self.assertRaises(DataDownloadError):
            self.aqmesh.scrape_device("123", mock_start, mock_end)

    def test_403(self):
        mock_get_resp = build_mock_response(status=403, raise_for_status=HTTPError())
        mock_get = Mock(return_value=mock_get_resp)
        session_return = Mock(get=mock_get)
        self.aqmesh.session = session_return
        mock_start = MagicMock()
        mock_end = MagicMock()

        with self.assertRaises(DataDownloadError):
            self.aqmesh.scrape_device("123", mock_start, mock_end)

    def test_401(self):
        mock_get_resp = build_mock_response(status=401, raise_for_status=HTTPError())
        mock_get = Mock(return_value=mock_get_resp)
        session_return = Mock(get=mock_get)
        self.aqmesh.session = session_return
        mock_start = MagicMock()
        mock_end = MagicMock()

        with self.assertRaises(DataDownloadError):
            self.aqmesh.scrape_device("123", mock_start, mock_end)


class TestZephyr(unittest.TestCase):
    # Zephyr just requires a single GET request to obtain the data
    cfg = defaultdict(str)
    fields = []
    zephyr = Zephyr.Zephyr(cfg, fields)

    def test_success(self):
        mock_get_resp = build_mock_response(
            status=200, json_data={"CO2": [1, 2, 3], "NO": [4, 5, 6]}
        )
        mock_get = Mock(return_value=mock_get_resp)
        session_return = Mock(get=mock_get)
        self.zephyr.session = session_return
        mock_start = datetime(2020, 4, 3, 15, 35, 00)
        mock_end = datetime(2020, 5, 3, 16, 28, 29)

        # Make same substitution with device ID into the GET params and assert
        # that these are used in the function call
        mock_url = self.zephyr.data_url
        mock_url = mock_url.substitute(
            device="123",
            token=self.zephyr.api_token,
            start="20200403153500",
            end="20200503162829",
        )
        try:
            res = self.zephyr.scrape_device("123", mock_start, mock_end)
            self.assertEqual(res, {"CO2": [1, 2, 3], "NO": [4, 5, 6]})
            mock_get.assert_called_once_with(mock_url, headers=self.zephyr.data_headers)
        except:
            self.fail("Connect raised exception with status code 200")

    # Test that custom DataDownloadError is raised under a variety of failure
    # conditions
    def test_400(self):
        mock_get_resp = build_mock_response(status=400, raise_for_status=HTTPError())
        mock_get = Mock(return_value=mock_get_resp)
        session_return = Mock(get=mock_get)
        self.zephyr.session = session_return
        mock_start = MagicMock()
        mock_end = MagicMock()

        with self.assertRaises(DataDownloadError):
            self.zephyr.scrape_device("123", mock_start, mock_end)

    def test_404(self):
        mock_get_resp = build_mock_response(status=404, raise_for_status=HTTPError())
        mock_get = Mock(return_value=mock_get_resp)
        session_return = Mock(get=mock_get)
        self.zephyr.session = session_return
        mock_start = MagicMock()
        mock_end = MagicMock()

        with self.assertRaises(DataDownloadError):
            self.zephyr.scrape_device("123", mock_start, mock_end)

    def test_403(self):
        mock_get_resp = build_mock_response(status=403, raise_for_status=HTTPError())
        mock_get = Mock(return_value=mock_get_resp)
        session_return = Mock(get=mock_get)
        self.zephyr.session = session_return
        mock_start = MagicMock()
        mock_end = MagicMock()

        with self.assertRaises(DataDownloadError):
            self.zephyr.scrape_device("123", mock_start, mock_end)

    def test_401(self):
        mock_get_resp = build_mock_response(status=401, raise_for_status=HTTPError())
        mock_get = Mock(return_value=mock_get_resp)
        session_return = Mock(get=mock_get)
        self.zephyr.session = session_return
        mock_start = MagicMock()
        mock_end = MagicMock()

        with self.assertRaises(DataDownloadError):
            self.zephyr.scrape_device("123", mock_start, mock_end)


class TestMyQuantAQ(unittest.TestCase):
    # Can't test HTTP errors with QuantAQ as it wraps them up for us in their
    # API. Instead can test their errors are handled appropriately
    cfg = defaultdict(str)
    fields = []
    myquantaq = MyQuantAQ.MyQuantAQ(cfg, fields)

    def test_success(self):
        mock_resp = {"CO2": [1, 2, 3], "NO2": [4, 5, 6]}
        mock_get_data = Mock(return_value=mock_resp)
        mock_api_obj = Mock(get_data=mock_get_data)
        self.myquantaq.api_obj = mock_api_obj
        mock_start = datetime(2020, 4, 3, 15, 35, 00)
        mock_end = datetime(2020, 5, 3, 16, 28, 29)
        try:
            res = self.myquantaq.scrape_device("foo", mock_start, mock_end)
            self.assertEqual(
                res,
                {
                    "raw": {"CO2": [1, 2, 3], "NO2": [4, 5, 6]},
                    "final": {"CO2": [1, 2, 3], "NO2": [4, 5, 6]},
                },
            )
            exp_filter = self.myquantaq.query_string.substitute(
                start="2020-04-03", end="2020-05-04"
            )
            exp_calls = [
                call(sn="foo", final_data=False, params=dict(filter=exp_filter)),
                call(sn="foo", final_data=True, params=dict(filter=exp_filter)),
            ]
            self.assertEqual(mock_get_data.mock_calls, exp_calls)
        except:
            self.fail("Connect raised exception with status code 200")

    def test_failure(self):
        mock_get_data = Mock(side_effect=DataReadError)
        mock_api_obj = Mock(get_data=mock_get_data)
        self.myquantaq.api_obj = mock_api_obj
        mock_start = MagicMock()
        mock_end = MagicMock()
        with self.assertRaises(DataDownloadError):
            self.myquantaq.scrape_device("foo", mock_start, mock_end)


if __name__ == "__main__":
    unittest.main()
