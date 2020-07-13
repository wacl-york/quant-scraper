"""
    test_log_device_status.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~

    Unit tests for Manufacturer.log_device_status() methods.
"""

import unittest
from collections import defaultdict
from unittest.mock import Mock
from requests.exceptions import HTTPError
import quantscraper.manufacturers.Aeroqual as Aeroqual
import quantscraper.manufacturers.AQMesh as AQMesh
import quantscraper.manufacturers.Zephyr as Zephyr
import quantscraper.manufacturers.MyQuantAQ as MyQuantAQ
import quantscraper.manufacturers.AURN as AURN
from quantscraper.utils import DataDownloadError
from utils import build_mock_response


class TestAeroqual(unittest.TestCase):

    cfg = defaultdict(str)
    fields = []
    aeroqual = Aeroqual.Aeroqual(cfg, fields)

    def test_200_success(self):
        successful_html = """
        <div>
        <table id='modulesTable'>
        <th><td>Header...</td></th>
        <tr>
            <td><input data-parameter='Slope' data-sensor='O2' value='5.2'></input></td>
            <td><input data-parameter='Offset' data-sensor='O2' value='1.2'></input></td>
        </tr>
        <tr>
            <td><input data-parameter='Slope' data-sensor='NO' value='2.8'></input></td>
            <td><input data-parameter='Offset' data-sensor='NO' value='1.7'></input></td>
        </tr>
        </table>
        </div>
        """
        successful_params = {
            "O2_Slope": "5.2",
            "O2_Offset": "1.2",
            "NO_Slope": "2.8",
            "NO_Offset": "1.7",
        }

        mock_select_device = Mock()
        self.aeroqual.select_device = mock_select_device

        # Mock 200 response on get, and select_device doesn't raise error
        mock_get = Mock(
            return_value=build_mock_response(status=200, text=successful_html)
        )

        session_return = Mock(get=mock_get)
        self.aeroqual.session = session_return
        try:
            res = self.aeroqual.log_device_status("foo")
            mock_get.assert_called_once_with(self.aeroqual.calibration_url)
            self.assertEqual(res, successful_params)

        except:
            self.fail("Connect raised exception with status code 200")

    def test_no_modulesTable(self):
        # When don't have a table with required id, raise DataDownloadError
        html = """
        <div>
        <table>
        <th><td>Header...</td></th>
        <tr>
            <td><input data-parameter='Slope' data-sensor='O2' value='5.2'></input></td>
            <td><input data-parameter='Offset' data-sensor='O2' value='1.2'></input></td>
        </tr>
        <tr>
            <td><input data-parameter='Slope' data-sensor='NO' value='2.8'></input></td>
            <td><input data-parameter='Offset' data-sensor='NO' value='1.7'></input></td>
        </tr>
        </table>
        </div>
        """

        mock_select_device = Mock()
        self.aeroqual.select_device = mock_select_device

        # Mock 200 response on get, and select_device doesn't raise error
        mock_get = Mock(return_value=build_mock_response(status=200, text=html))

        session_return = Mock(get=mock_get)
        self.aeroqual.session = session_return

        with self.assertRaises(DataDownloadError):
            self.aeroqual.log_device_status("foo")
            mock_get.assert_called_once_with(self.aeroqual.calibration_url)

    def test_invalid_inputs(self):
        # When don't have a input tags with all 3 required attributes,
        # doesn't add them to dictionary
        # DataDownloadError
        html = """
        <div>
        <table id='modulesTable'>
        <th><td>Header...</td></th>
        <tr>
            <td><input data-parameter='Slope' data-sensor='O2'></input></td>
            <td><input data-parameter='Offset' value='1.2'></input></td>
            <td><input data-sensor='O2' value='1.2'></input></td>
            <td><input value='1.2'></input></td>
            <td><input data-sensor='O2'></input></td>
        </tr>
        <tr>
            <td><input data-parameter='Slope' data-sensor='NO' value='2.8'></input></td>
            <td><input data-parameter='Offset' data-sensor='NO' value='1.7'></input></td>
        </tr>
        </table>
        </div>
        """
        successful_params = {"NO_Slope": "2.8", "NO_Offset": "1.7"}

        mock_select_device = Mock()
        self.aeroqual.select_device = mock_select_device

        # Mock 200 response on get, and select_device doesn't raise error
        mock_get = Mock(return_value=build_mock_response(status=200, text=html))

        session_return = Mock(get=mock_get)
        self.aeroqual.session = session_return
        try:
            res = self.aeroqual.log_device_status("foo")
            mock_get.assert_called_once_with(self.aeroqual.calibration_url)
            self.assertEqual(res, successful_params)

        except:
            self.fail("Connect raised exception with status code 200")

    def test_no_valid_inputs(self):
        # When don't have any input tags with all 3 required attributes
        # then should still return empty dict
        html = """
        <div>
        <table id='modulesTable'>
        <th><td>Header...</td></th>
        <tr>
            <td>O2 offset =1.3</td>
            <td>NO2 gain = 1.2</td>
        </table>
        </div>
        """
        successful_params = {}
        mock_select_device = Mock()
        self.aeroqual.select_device = mock_select_device

        # Mock 200 response on get, and select_device doesn't raise error
        mock_get = Mock(return_value=build_mock_response(status=200, text=html))

        session_return = Mock(get=mock_get)
        self.aeroqual.session = session_return
        try:
            res = self.aeroqual.log_device_status("foo")
            mock_get.assert_called_once_with(self.aeroqual.calibration_url)
            self.assertEqual(res, successful_params)

        except:
            self.fail("Connect raised exception with status code 200")

    def test_select_device_fails(self):
        # If select_device() throws an error it should be propagated up
        # Mock 200 response on get, and select_device doesn't raise error
        html = """
        <div>
        <table id='modulesTable'>
        <th><td>Header...</td></th>
        <tr>
            <td>O2 offset =1.3</td>
            <td>NO2 gain = 1.2</td>
        </table>
        </div>
        """
        mock_get = Mock(return_value=build_mock_response(status=200, text=html))

        mock_select_device = Mock(side_effect=DataDownloadError(""))
        self.aeroqual.select_device = mock_select_device

        session_return = Mock(get=mock_get)
        self.aeroqual.session = session_return
        with self.assertRaises(DataDownloadError):
            self.aeroqual.log_device_status("foo")

    def test_get_400(self):
        # If the get call gets a non-200 response, the function should throw an
        # error
        mock_get = Mock(
            return_value=build_mock_response(status=400, raise_for_status=HTTPError())
        )

        mock_select_device = Mock()
        self.aeroqual.select_device = mock_select_device

        session_return = Mock(get=mock_get)
        self.aeroqual.session = session_return
        with self.assertRaises(DataDownloadError):
            self.aeroqual.log_device_status("foo")

    def test_get_404(self):
        # If the get call gets a non-200 response, the function should throw an
        # error
        mock_get = Mock(
            return_value=build_mock_response(status=404, raise_for_status=HTTPError())
        )

        mock_select_device = Mock()
        self.aeroqual.select_device = mock_select_device

        session_return = Mock(get=mock_get)
        self.aeroqual.session = session_return
        with self.assertRaises(DataDownloadError):
            self.aeroqual.log_device_status("foo")


class TestAQMesh(unittest.TestCase):

    cfg = defaultdict(str)
    fields = []
    aqmesh = AQMesh.AQMesh(cfg, fields)

    def test_success(self):
        clean_data = {
            "Foo": "bar",
            "Channels": [
                {"SensorLabel": "O3", "Unit": "ppm", "Slope": "2.3", "Offset": "-32.2"},
                {"SensorLabel": "CO2", "Unit": "ppr", "Slope": "5.1", "Offset": "2"},
            ],
        }

        clean_params = {
            "O3(ppm)_Slope": "2.3",
            "O3(ppm)_Offset": "-32.2",
            "CO2(ppr)_Slope": "5.1",
            "CO2(ppr)_Offset": "2",
        }

        mock_post_resp = build_mock_response(status=200, json_data=clean_data)
        mock_post = Mock(return_value=mock_post_resp)
        session_return = Mock(post=mock_post)
        self.aqmesh.session = session_return

        try:
            res = self.aqmesh.log_device_status("123")
            self.assertEqual(res, clean_params)
            mock_post.assert_called_once_with(
                self.aqmesh.data_url,
                headers=self.aqmesh.data_headers,
                params={"CRUD": "read", "Call": "deviceinformation", "UniqueId": "123"},
            )
        except:
            self.fail("Connect raised exception with status code 200")

    def test_error_400(self):
        # DataDownloadError should be raised when request is non-200.
        # Here just test 400 and 404
        mock_post_resp = build_mock_response(status=400, raise_for_status=HTTPError())
        mock_post = Mock(return_value=mock_post_resp)
        session_return = Mock(post=mock_post)
        self.aqmesh.session = session_return

        with self.assertRaises(DataDownloadError):
            self.aqmesh.log_device_status("123")
            mock_post.assert_called_once_with(
                self.aqmesh.data_url,
                headers=self.aqmesh.data_headers,
                params={"CRUD": "read", "Call": "deviceinformation", "UniqueId": "123"},
            )

    def test_error_404(self):
        # DataDownloadError should be raised when request is non-200.
        # Here just test 400 and 404
        mock_post_resp = build_mock_response(status=404, raise_for_status=HTTPError())
        mock_post = Mock(return_value=mock_post_resp)
        session_return = Mock(post=mock_post)
        self.aqmesh.session = session_return

        with self.assertRaises(DataDownloadError):
            self.aqmesh.log_device_status("123")
            mock_post.assert_called_once_with(
                self.aqmesh.data_url,
                headers=self.aqmesh.data_headers,
                params={"CRUD": "read", "Call": "deviceinformation", "UniqueId": "123"},
            )

    def test_json_type_error(self):
        # Can't explicitly test for JSON Decode error but can test for type
        # error in the retrieved JSON file
        mock_post_resp = Mock(status_code=200, json=Mock(side_effect=TypeError("")))

        mock_post = Mock(return_value=mock_post_resp)
        session_return = Mock(post=mock_post)
        self.aqmesh.session = session_return

        with self.assertRaises(DataDownloadError):
            self.aqmesh.log_device_status("123")
            mock_post.assert_called_once_with(
                self.aqmesh.data_url,
                headers=self.aqmesh.data_headers,
                params={"CRUD": "read", "Call": "deviceinformation", "UniqueId": "123"},
            )

    def test_no_channels(self):
        # If the Channels attribute isn't available then should get an empty
        # list
        clean_data = {
            "Foo": "bar",
            "Data": [
                {"SensorLabel": "O3", "Unit": "ppm", "Slope": "2.3", "Offset": "-32.2"},
                {"SensorLabel": "CO2", "Unit": "ppr", "Slope": "5.1", "Offset": "2"},
            ],
        }

        clean_params = {}

        mock_post_resp = build_mock_response(status=200, json_data=clean_data)
        mock_post = Mock(return_value=mock_post_resp)
        session_return = Mock(post=mock_post)
        self.aqmesh.session = session_return

        try:
            res = self.aqmesh.log_device_status("123")
            self.assertEqual(res, clean_params)
            mock_post.assert_called_once_with(
                self.aqmesh.data_url,
                headers=self.aqmesh.data_headers,
                params={"CRUD": "read", "Call": "deviceinformation", "UniqueId": "123"},
            )
        except:
            self.fail("Connect raised exception with status code 200")

    def test_empty_channel(self):
        # Channels list having no entries should return an empty dict
        clean_data = {"Foo": "bar", "Channels": []}

        clean_params = {}

        mock_post_resp = build_mock_response(status=200, json_data=clean_data)
        mock_post = Mock(return_value=mock_post_resp)
        session_return = Mock(post=mock_post)
        self.aqmesh.session = session_return

        try:
            res = self.aqmesh.log_device_status("242")
            self.assertEqual(res, clean_params)
            mock_post.assert_called_once_with(
                self.aqmesh.data_url,
                headers=self.aqmesh.data_headers,
                params={"CRUD": "read", "Call": "deviceinformation", "UniqueId": "242"},
            )
        except:
            self.fail("Connect raised exception with status code 200")

    def test_no_sensor_label(self):
        # If a Channel object lacks the SensorLabel parameter then
        # simply shouldn't have any values from this channel in output
        clean_data = {
            "Foo": "bar",
            "Channels": [
                {"Val": "O3", "Unit": "ppm", "Slope": "2.3", "Offset": "-32.2"},
                {"SensorLabel": "CO2", "Unit": "ppr", "Slope": "5.1", "Offset": "2"},
            ],
        }

        clean_params = {
            "CO2(ppr)_Slope": "5.1",
            "CO2(ppr)_Offset": "2",
        }

        mock_post_resp = build_mock_response(status=200, json_data=clean_data)
        mock_post = Mock(return_value=mock_post_resp)
        session_return = Mock(post=mock_post)
        self.aqmesh.session = session_return

        try:
            res = self.aqmesh.log_device_status("123")
            self.assertEqual(res, clean_params)
            mock_post.assert_called_once_with(
                self.aqmesh.data_url,
                headers=self.aqmesh.data_headers,
                params={"CRUD": "read", "Call": "deviceinformation", "UniqueId": "123"},
            )
        except:
            self.fail("Connect raised exception with status code 200")

    def test_no_unit(self):
        # If a Channel object lacks the Unit parameter then
        # simply shouldn't have any values from this channel in output
        clean_data = {
            "Foo": "bar",
            "Channels": [
                {"SensorLabel": "O3", "Unit": "ppm", "Slope": "2.3", "Offset": "-32.2"},
                {"SensorLabel": "CO2", "units": "ppr", "Slope": "5.1", "Offset": "2"},
            ],
        }

        clean_params = {
            "O3(ppm)_Slope": "2.3",
            "O3(ppm)_Offset": "-32.2",
        }

        mock_post_resp = build_mock_response(status=200, json_data=clean_data)
        mock_post = Mock(return_value=mock_post_resp)
        session_return = Mock(post=mock_post)
        self.aqmesh.session = session_return

        try:
            res = self.aqmesh.log_device_status("123")
            self.assertEqual(res, clean_params)
            mock_post.assert_called_once_with(
                self.aqmesh.data_url,
                headers=self.aqmesh.data_headers,
                params={"CRUD": "read", "Call": "deviceinformation", "UniqueId": "123"},
            )
        except:
            self.fail("Connect raised exception with status code 200")

    def test_no_slope_offset(self):
        # If have no Slope or Offset attributes for a given channel then should
        # still return parameters that are available
        clean_data = {
            "Foo": "bar",
            "Channels": [
                {"SensorLabel": "O3", "Unit": "ppm", "Slope": "2.3", "Offset": "-32.2"},
                {"SensorLabel": "CO2", "Unit": "ppr", "Offset": "2"},
                {"SensorLabel": "NO", "Unit": "mgm3", "Slope": "82.2",},
                {"SensorLabel": "CO", "Unit": "ppr",},
            ],
        }

        clean_params = {
            "O3(ppm)_Slope": "2.3",
            "O3(ppm)_Offset": "-32.2",
            "CO2(ppr)_Offset": "2",
            "NO(mgm3)_Slope": "82.2",
        }

        mock_post_resp = build_mock_response(status=200, json_data=clean_data)
        mock_post = Mock(return_value=mock_post_resp)
        session_return = Mock(post=mock_post)
        self.aqmesh.session = session_return

        try:
            res = self.aqmesh.log_device_status("123")
            self.assertEqual(res, clean_params)
            mock_post.assert_called_once_with(
                self.aqmesh.data_url,
                headers=self.aqmesh.data_headers,
                params={"CRUD": "read", "Call": "deviceinformation", "UniqueId": "123"},
            )
        except:
            self.fail("Connect raised exception with status code 200")


class TestZephyr(unittest.TestCase):
    # This method isn't currently implemented for Zephyr, so test it returns
    # an empty dict
    cfg = defaultdict(str)
    fields = []
    zephyr = Zephyr.Zephyr(cfg, fields)

    def test_success(self):
        try:
            res = self.zephyr.log_device_status("123")
            self.assertEqual(res, {})
        except:
            self.fail("Connect raised exception with status code 200")


class TestMyQuantAQ(unittest.TestCase):
    # This method isn't currently implemented for QuantAQ, so test it returns
    # an empty dict
    cfg = defaultdict(str)
    fields = []
    myquantaq = MyQuantAQ.MyQuantAQ(cfg, fields)

    def test_success(self):
        try:
            res = self.myquantaq.log_device_status("foo")
            self.assertEqual(res, {})
        except:
            self.fail("Connect raised exception with status code 200")


class TestAURN(unittest.TestCase):
    # This method isn't currently implemented for AURN, so test it returns
    # an empty dict
    cfg = defaultdict(str)
    fields = []
    myaurn = AURN.AURN(cfg, fields)

    def test_success(self):
        try:
            res = self.myaurn.log_device_status("foo")
            self.assertEqual(res, {})
        except:
            self.fail("Connect raised exception with status code 200")


if __name__ == "__main__":
    unittest.main()
