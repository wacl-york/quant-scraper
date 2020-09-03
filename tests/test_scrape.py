"""
    test_scrape.py
    ~~~~~~~~~~~~~~~

    Unit tests for Manufacturer.scrape_device() methods.
"""

import os
import unittest
from collections import defaultdict
from unittest.mock import Mock, call
from datetime import date
from requests.exceptions import HTTPError
from quantaq.baseapi import DataReadError
import quantscraper.manufacturers.Aeroqual as Aeroqual
import quantscraper.manufacturers.AQMesh as AQMesh
import quantscraper.manufacturers.Zephyr as Zephyr
import quantscraper.manufacturers.MyQuantAQ as MyQuantAQ
import quantscraper.manufacturers.AURN as AURN
from quantscraper.utils import DataDownloadError
from utils import build_mock_response

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

    def test_select_device_success(self):
        # Select device passes when returns HTTP 200
        aeroqual = Aeroqual.Aeroqual(self.cfg, self.fields)
        aeroqual.select_device_url = "foo.com"
        mock_post = Mock(return_value=build_mock_response(status=200))
        session_return = Mock(post=mock_post)
        aeroqual.session = session_return

        aeroqual.select_device("foo")
        mock_post.assert_called_once_with(
            "foo.com",
            json=[aeroqual.select_device_string.substitute(device="foo")],
            headers=aeroqual.select_device_headers,
        )

    def test_select_device_400(self):
        # Select device raises error when POST returns 400
        aeroqual = Aeroqual.Aeroqual(self.cfg, self.fields)
        aeroqual.select_device_url = "foo.com"
        mock_post = Mock(
            return_value=build_mock_response(status=400, raise_for_status=HTTPError())
        )
        session_return = Mock(post=mock_post)
        aeroqual.session = session_return

        with self.assertRaises(DataDownloadError):
            aeroqual.select_device("foo")
            mock_post.assert_called_once_with(
                aeroqual.select_device_url,
                json=[aeroqual.select_device_string.substitute(device="foo")],
                headers=aeroqual.select_device_headers,
            )

    def test_select_device_404(self):
        # Select device raises error when POST returns 404
        aeroqual = Aeroqual.Aeroqual(self.cfg, self.fields)
        aeroqual.select_device_url = "foo.com"
        mock_post = Mock(
            return_value=build_mock_response(status=404, raise_for_status=HTTPError())
        )
        session_return = Mock(post=mock_post)
        aeroqual.session = session_return

        with self.assertRaises(DataDownloadError):
            aeroqual.select_device("foo")
            mock_post.assert_called_once_with(
                aeroqual.select_device_url,
                json=[aeroqual.select_device_string.substitute(device="foo")],
                headers=aeroqual.select_device_headers,
            )

    def test_200_success(self):
        # Mock 200 response on select_device call and generate data posts and
        # download data get
        aeroqual = Aeroqual.Aeroqual(self.cfg, self.fields)
        mock_post = Mock(return_value=build_mock_response(status=200))
        mock_select_device = Mock()
        mock_get = Mock(return_value=build_mock_response(status=200))
        aeroqual.select_device = mock_select_device

        mock_start = date(2020, 4, 3)
        mock_end = date(2020, 5, 3)

        session_return = Mock(post=mock_post, get=mock_get)
        aeroqual.session = session_return
        aeroqual.scrape_device("foo", mock_start, mock_end)
        exp_params = aeroqual.data_params.copy()
        exp_params["Period"] = exp_params["Period"].substitute(
            start="04/03/2020", end="05/03/2020"
        )
        mock_post.assert_called_once_with(
            aeroqual.data_url, data=exp_params, headers=aeroqual.data_headers,
        )
        mock_get.assert_called_once_with(aeroqual.dl_url, headers=aeroqual.dl_headers)

    def test_retrieves_content(self):
        # Now test that actually download the content we expected
        aeroqual = Aeroqual.Aeroqual(self.cfg, self.fields)
        mock_post = Mock(return_value=build_mock_response(status=200))
        mock_select_device = Mock()
        mock_get = Mock(return_value=build_mock_response(status=200, text="DummyData"))
        aeroqual.select_device = mock_select_device

        mock_start = date(2020, 4, 3)
        mock_end = date(2020, 5, 3)

        exp_params = aeroqual.data_params.copy()
        exp_params["Period"] = exp_params["Period"].substitute(
            start="04/03/2020", end="05/03/2020"
        )

        session_return = Mock(post=mock_post, get=mock_get)
        aeroqual.session = session_return
        resp = aeroqual.scrape_device("foo", mock_start, mock_end)
        self.assertEqual(resp, "DummyData")
        mock_post.assert_called_once_with(
            aeroqual.data_url, data=exp_params, headers=aeroqual.data_headers,
        )
        mock_get.assert_called_once_with(aeroqual.dl_url, headers=aeroqual.dl_headers)

    def test_select_device_failure_400(self):
        aeroqual = Aeroqual.Aeroqual(self.cfg, self.fields)
        mock_post = Mock(return_value=build_mock_response(status=200))
        mock_select_device = Mock(side_effect=DataDownloadError(""))
        mock_get = Mock(return_value=build_mock_response(status=200))
        aeroqual.select_device = mock_select_device

        mock_start = date(2020, 4, 3)
        mock_end = date(2020, 5, 3)
        session_return = Mock(
            post=Mock(side_effect=mock_post), get=Mock(return_value=mock_get)
        )
        aeroqual.session = session_return
        with self.assertRaises(DataDownloadError):
            foo = aeroqual.scrape_device("foo", mock_start, mock_end)

    def test_generate_data_failure_400(self):
        aeroqual = Aeroqual.Aeroqual(self.cfg, self.fields)
        mock_post = Mock(
            return_value=build_mock_response(status=400, raise_for_status=HTTPError())
        )
        mock_select_device = Mock()
        mock_get = Mock(return_value=build_mock_response(status=200))
        aeroqual.select_device = mock_select_device

        session_return = Mock(
            post=Mock(side_effect=mock_post), get=Mock(return_value=mock_get)
        )
        mock_start = date(2020, 4, 3)
        mock_end = date(2020, 5, 3)
        aeroqual.session = session_return
        with self.assertRaises(DataDownloadError):
            aeroqual.scrape_device("foo", mock_start, mock_end)

    def test_generate_data_failure_404(self):
        aeroqual = Aeroqual.Aeroqual(self.cfg, self.fields)
        mock_post = Mock(
            return_value=build_mock_response(status=404, raise_for_status=HTTPError())
        )
        mock_select_device = Mock()
        mock_get = Mock(return_value=build_mock_response(status=200))
        aeroqual.select_device = mock_select_device
        session_return = Mock(
            post=Mock(side_effect=mock_post), get=Mock(return_value=mock_get)
        )
        mock_start = date(2020, 4, 3)
        mock_end = date(2020, 5, 3)
        aeroqual.session = session_return
        with self.assertRaises(DataDownloadError):
            aeroqual.scrape_device("foo", mock_start, mock_end)

    def test_download_data_failure_400(self):
        aeroqual = Aeroqual.Aeroqual(self.cfg, self.fields)
        mock_post = build_mock_response(status=200)
        mock_get = build_mock_response(status=400, raise_for_status=HTTPError())
        mock_select_device = Mock()
        aeroqual.select_device = mock_select_device
        session_return = Mock(
            post=Mock(side_effect=mock_post), get=Mock(return_value=mock_get)
        )
        mock_start = date(2020, 4, 3)
        mock_end = date(2020, 5, 3)
        aeroqual.session = session_return
        with self.assertRaises(DataDownloadError):
            aeroqual.scrape_device("foo", mock_start, mock_end)

    def test_download_data_failure_404(self):
        aeroqual = Aeroqual.Aeroqual(self.cfg, self.fields)
        mock_post = build_mock_response(status=200)
        mock_get = build_mock_response(status=400, raise_for_status=HTTPError())
        mock_select_device = Mock()
        aeroqual.select_device = mock_select_device
        session_return = Mock(
            post=Mock(side_effect=mock_post), get=Mock(return_value=mock_get)
        )
        mock_start = date(2020, 4, 3)
        mock_end = date(2020, 5, 3)
        aeroqual.session = session_return
        with self.assertRaises(DataDownloadError):
            aeroqual.scrape_device("foo", mock_start, mock_end)


class TestAQMesh(unittest.TestCase):

    # AQMesh just runs a single GET request to get the data,
    # which is returned in the 'Data' attribute of the resultant JSON
    cfg = defaultdict(str)
    cfg["time_convention"] = "reverse"
    cfg["averaging_window"] = "-5"
    os.environ["AQMESH_API_ID"] = "myid"
    os.environ["AQMESH_API_TOKEN"] = "mytoken"

    fields = []

    aqmesh = AQMesh.AQMesh(cfg, fields)

    def test_success(self):
        mock_get_resp = build_mock_response(status=200, json_data={"Data": [1, 2, 3]})
        mock_get = Mock(return_value=mock_get_resp)
        session_return = Mock(get=mock_get)
        self.aqmesh.session = session_return

        mock_start = date(2020, 4, 3)
        mock_end = date(2020, 5, 3)
        res = self.aqmesh.scrape_device("123", mock_start, mock_end)
        self.assertEqual(res, {"Data": [1, 2, 3]})
        mock_get.assert_called_once_with(
            "https://api.airmonitors.net/3.5/GET/myid/mytoken/stationdata/reverse/AVG-5/2020-04-03T00:00:00/2020-05-03T23:59:59/123"
        )

    # Test that custom DataDownloadError is raised under a variety of failure
    # conditions
    def test_400(self):
        mock_get_resp = build_mock_response(status=400, raise_for_status=HTTPError())
        mock_get = Mock(return_value=mock_get_resp)
        session_return = Mock(get=mock_get)
        self.aqmesh.session = session_return
        mock_start = date(2020, 4, 3)
        mock_end = date(2020, 5, 3)

        with self.assertRaises(DataDownloadError):
            self.aqmesh.scrape_device("123", mock_start, mock_end)

    def test_404(self):
        mock_get_resp = build_mock_response(status=404, raise_for_status=HTTPError())
        mock_get = Mock(return_value=mock_get_resp)
        session_return = Mock(get=mock_get)
        self.aqmesh.session = session_return
        mock_start = date(2020, 4, 3)
        mock_end = date(2020, 5, 3)

        with self.assertRaises(DataDownloadError):
            self.aqmesh.scrape_device("123", mock_start, mock_end)

    def test_403(self):
        mock_get_resp = build_mock_response(status=403, raise_for_status=HTTPError())
        mock_get = Mock(return_value=mock_get_resp)
        session_return = Mock(get=mock_get)
        self.aqmesh.session = session_return
        mock_start = date(2020, 4, 3)
        mock_end = date(2020, 5, 3)

        with self.assertRaises(DataDownloadError):
            self.aqmesh.scrape_device("123", mock_start, mock_end)

    def test_401(self):
        mock_get_resp = build_mock_response(status=401, raise_for_status=HTTPError())
        mock_get = Mock(return_value=mock_get_resp)
        session_return = Mock(get=mock_get)
        self.aqmesh.session = session_return
        mock_start = date(2020, 4, 3)
        mock_end = date(2020, 5, 3)

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
        mock_start = date(2020, 4, 3)
        mock_end = date(2020, 5, 3)

        # Make same substitution with device ID into the GET params and assert
        # that these are used in the function call
        mock_url = self.zephyr.data_url
        mock_url = mock_url.substitute(
            device="123",
            token=self.zephyr.api_token,
            start="20200403000000",
            end="20200504000000",
        )
        res = self.zephyr.scrape_device("123", mock_start, mock_end)
        self.assertEqual(res, {"CO2": [1, 2, 3], "NO": [4, 5, 6]})
        mock_get.assert_called_once_with(mock_url, headers=self.zephyr.data_headers)

    # Test that custom DataDownloadError is raised under a variety of failure
    # conditions
    def test_400(self):
        mock_get_resp = build_mock_response(status=400, raise_for_status=HTTPError())
        mock_get = Mock(return_value=mock_get_resp)
        session_return = Mock(get=mock_get)
        self.zephyr.session = session_return
        mock_start = date(2020, 3, 17)
        mock_end = date(2020, 3, 17)

        with self.assertRaises(DataDownloadError):
            self.zephyr.scrape_device("123", mock_start, mock_end)

    def test_404(self):
        mock_get_resp = build_mock_response(status=404, raise_for_status=HTTPError())
        mock_get = Mock(return_value=mock_get_resp)
        session_return = Mock(get=mock_get)
        self.zephyr.session = session_return
        mock_start = date(2020, 3, 17)
        mock_end = date(2020, 3, 17)

        with self.assertRaises(DataDownloadError):
            self.zephyr.scrape_device("123", mock_start, mock_end)

    def test_403(self):
        mock_get_resp = build_mock_response(status=403, raise_for_status=HTTPError())
        mock_get = Mock(return_value=mock_get_resp)
        session_return = Mock(get=mock_get)
        self.zephyr.session = session_return
        mock_start = date(2020, 3, 17)
        mock_end = date(2020, 3, 17)

        with self.assertRaises(DataDownloadError):
            self.zephyr.scrape_device("123", mock_start, mock_end)

    def test_401(self):
        mock_get_resp = build_mock_response(status=401, raise_for_status=HTTPError())
        mock_get = Mock(return_value=mock_get_resp)
        session_return = Mock(get=mock_get)
        self.zephyr.session = session_return
        mock_start = date(2020, 3, 17)
        mock_end = date(2020, 3, 17)

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
        mock_start = date(2020, 4, 3)
        mock_end = date(2020, 5, 3)
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

    def test_failure(self):
        mock_get_data = Mock(side_effect=DataReadError)
        mock_api_obj = Mock(get_data=mock_get_data)
        self.myquantaq.api_obj = mock_api_obj
        mock_start = date(2020, 4, 3)
        mock_end = date(2020, 5, 3)
        with self.assertRaises(DataDownloadError):
            self.myquantaq.scrape_device("foo", mock_start, mock_end)


class TestAURN(unittest.TestCase):

    # AURN just runs a single POST request to get the data,
    cfg = defaultdict(str)
    fields = []
    aurn = AURN.AURN(cfg, fields)

    def test_success(self):
        mock_post_resp = build_mock_response(
            status=200, json_data={"foo": [1, 2, 3], "bar": [5, 8, 9]}
        )
        mock_post = Mock(return_value=mock_post_resp)
        session_return = Mock(post=mock_post)
        self.aurn.session = session_return
        self.aurn.timeseries_ids = ["foo", "bar"]
        self.aurn.api_url = "foo.com"

        # Make same substitution with device ID into the GET params and assert
        # that these are used in the function call
        mock_start = date(2020, 4, 3)
        mock_end = date(2020, 5, 3)
        res = self.aurn.scrape_device("123", mock_start, mock_end)
        self.assertEqual(res, {"foo": [1, 2, 3], "bar": [5, 8, 9]})
        mock_post.assert_called_once_with(
            "foo.com",
            json={
                "timespan": "2020-04-03T00:00:00Z/2020-05-03T23:59:59Z",
                "timeseries": ["foo", "bar"],
            },
            headers={"Content-Type": "application/json", "Accept": "application/json",},
        )

    # Test that custom DataDownloadError is raised under a variety of failure
    # conditions
    def test_400(self):
        mock_post_resp = build_mock_response(status=400, raise_for_status=HTTPError())
        mock_post = Mock(return_value=mock_post_resp)
        session_return = Mock(post=mock_post)
        self.aurn.session = session_return
        mock_start = date(2020, 4, 3)
        mock_end = date(2020, 5, 3)

        with self.assertRaises(DataDownloadError):
            self.aurn.scrape_device("123", mock_start, mock_end)

    def test_404(self):
        mock_post_resp = build_mock_response(status=404, raise_for_status=HTTPError())
        mock_post = Mock(return_value=mock_post_resp)
        session_return = Mock(post=mock_post)
        self.aurn.session = session_return
        mock_start = date(2020, 4, 3)
        mock_end = date(2020, 5, 3)

        with self.assertRaises(DataDownloadError):
            self.aurn.scrape_device("123", mock_start, mock_end)

    def test_403(self):
        mock_post_resp = build_mock_response(status=403, raise_for_status=HTTPError())
        mock_post = Mock(return_value=mock_post_resp)
        session_return = Mock(post=mock_post)
        self.aurn.session = session_return
        mock_start = date(2020, 4, 3)
        mock_end = date(2020, 5, 3)

        with self.assertRaises(DataDownloadError):
            self.aurn.scrape_device("123", mock_start, mock_end)

    def test_401(self):
        mock_post_resp = build_mock_response(status=401, raise_for_status=HTTPError())
        mock_post = Mock(return_value=mock_post_resp)
        session_return = Mock(post=mock_post)
        self.aurn.session = session_return
        mock_start = date(2020, 4, 3)
        mock_end = date(2020, 5, 3)

        with self.assertRaises(DataDownloadError):
            self.aurn.scrape_device("123", mock_start, mock_end)


if __name__ == "__main__":
    unittest.main()
