"""
    test_factories.py
    ~~~~~~~~~~~~~~~~~

    Unit tests for factory functions, that are used to instantiate objects.
"""

import unittest
from copy import deepcopy
import os
from collections import defaultdict
from quantscraper.factories import (
    manufacturer_factory,
    device_factory,
    setup_manufacturers,
)
from quantscraper.manufacturers.Manufacturer import Manufacturer, Device

# Setup dummy env variables
os.environ["AEROQUAL_USER"] = "foo"
os.environ["AEROQUAL_PW"] = "foo"
os.environ["AQMESH_USER"] = "foo"
os.environ["AQMESH_PW"] = "foo"
os.environ["ZEPHYR_USER"] = "foo"
os.environ["ZEPHYR_PW"] = "foo"
os.environ["QUANTAQ_API_TOKEN"] = "foo"


class TestManufacturerFactory(unittest.TestCase):
    cfg = defaultdict(str)
    cfg["properties"] = defaultdict(str)
    cfg["fields"] = []

    def test_aeroqual_success(self):
        self.cfg["name"] = "Aeroqual"

        # Shouldn't raise any errors
        try:
            res = manufacturer_factory(self.cfg)
            self.assertIsInstance(res, Manufacturer)
        except:
            self.fail("Error was unexpectedly raised.")

    def test_aqmesh_success(self):
        self.cfg["name"] = "Aeroqual"

        # Shouldn't raise any errors
        try:
            res = manufacturer_factory(self.cfg)
            self.assertIsInstance(res, Manufacturer)
        except:
            self.fail("Error was unexpectedly raised.")

    def test_zephyr_success(self):
        self.cfg["name"] = "Zephyr"

        # Shouldn't raise any errors
        try:
            res = manufacturer_factory(self.cfg)
            self.assertIsInstance(res, Manufacturer)
        except:
            self.fail("Error was unexpectedly raised.")

    def test_quantaq_success(self):
        self.cfg["name"] = "QuantAQ"

        # Shouldn't raise any errors
        try:
            res = manufacturer_factory(self.cfg)
            self.assertIsInstance(res, Manufacturer)
        except:
            self.fail("Error was unexpectedly raised.")

    def test_key_error_raised(self):
        # Typo on quantAQ, so factory should raise KeyError
        self.cfg["name"] = "quantAQ"

        with self.assertRaises(KeyError):
            manufacturer_factory(self.cfg)


class TestDeviceFactory(unittest.TestCase):
    def test_success(self):
        props = {"id": "foo", "webid": "bar", "location": "york", "a": "too"}

        try:
            dev = device_factory(props)
            # Should set all 3 required attrs, plus any additional ones
            self.assertIsInstance(dev, Device)
            self.assertEqual(dev.device_id, "foo")
            self.assertEqual(dev.web_id, "bar")
            self.assertEqual(dev.location, "york")
            self.assertEqual(dev.a, "too")
        except:
            self.fail("Error was unexpectedly raised.")

    def test_miss_id(self):
        props = {"webid": "bar", "location": "york", "a": "too"}

        with self.assertRaises(KeyError):
            device_factory(props)

    def test_miss_webid(self):
        props = {"id": "foo", "location": "york", "a": "too"}

        with self.assertRaises(KeyError):
            device_factory(props)

    def test_miss_location(self):
        props = {"id": "foo", "webid": "bar", "a": "too"}

        with self.assertRaises(KeyError):
            device_factory(props)


class TestSetupManufacturers(unittest.TestCase):
    # Tests the setup_manufacturers() function, which sets up both Manufactuers
    # and Devices
    valid_config = [
        {
            "name": "Aeroqual",
            "properties": defaultdict(str),
            "fields": [],
            "devices": [
                {"id": "AQY10", "webid": "AQY10-a", "location": "foo"},
                {"id": "AQY81", "webid": "AQY81-b", "location": "bar"},
            ],
        },
        {
            "name": "AQMesh",
            "properties": defaultdict(str),
            "fields": [],
            "devices": [
                {"id": "AQM18", "webid": "AQM18-c", "location": "cat"},
                {"id": "AQM99", "webid": "AQM99-d", "location": "dog"},
            ],
        },
        {
            "name": "Zephyr",
            "properties": defaultdict(str),
            "fields": [],
            "devices": [
                {"id": "Zep33", "webid": "Zep33-e", "location": "echo"},
                {"id": "Zep22", "webid": "Zep22-f", "location": "frank"},
            ],
        },
    ]

    def test_success(self):
        devs = ["AQM18", "AQY81", "Zep22", "Zep33"]
        res = setup_manufacturers(deepcopy(self.valid_config), devs)
        self.assertEqual(len(res), 3)
        self.assertEqual(len(res[0].devices), 1)
        self.assertEqual(len(res[1].devices), 1)
        self.assertEqual(len(res[2].devices), 2)
        self.assertEqual(res[0].devices[0].device_id, "AQY81")
        self.assertEqual(res[0].devices[0].web_id, "AQY81-b")
        self.assertEqual(res[0].devices[0].location, "bar")
        self.assertEqual(res[1].devices[0].device_id, "AQM18")
        self.assertEqual(res[1].devices[0].web_id, "AQM18-c")
        self.assertEqual(res[1].devices[0].location, "cat")
        self.assertEqual(res[2].devices[0].device_id, "Zep33")
        self.assertEqual(res[2].devices[0].web_id, "Zep33-e")
        self.assertEqual(res[2].devices[0].location, "echo")
        self.assertEqual(res[2].devices[1].device_id, "Zep22")
        self.assertEqual(res[2].devices[1].web_id, "Zep22-f")
        self.assertEqual(res[2].devices[1].location, "frank")

    def test_success_all_devices(self):
        res = setup_manufacturers(deepcopy(self.valid_config))
        self.assertEqual(len(res), 3)
        self.assertEqual(len(res[0].devices), 2)
        self.assertEqual(len(res[1].devices), 2)
        self.assertEqual(len(res[2].devices), 2)
        self.assertEqual(res[0].devices[0].device_id, "AQY10")
        self.assertEqual(res[0].devices[0].web_id, "AQY10-a")
        self.assertEqual(res[0].devices[0].location, "foo")
        self.assertEqual(res[0].devices[1].device_id, "AQY81")
        self.assertEqual(res[0].devices[1].web_id, "AQY81-b")
        self.assertEqual(res[0].devices[1].location, "bar")

        self.assertEqual(res[1].devices[0].device_id, "AQM18")
        self.assertEqual(res[1].devices[0].web_id, "AQM18-c")
        self.assertEqual(res[1].devices[0].location, "cat")
        self.assertEqual(res[1].devices[1].device_id, "AQM99")
        self.assertEqual(res[1].devices[1].web_id, "AQM99-d")
        self.assertEqual(res[1].devices[1].location, "dog")

        self.assertEqual(res[2].devices[0].device_id, "Zep33")
        self.assertEqual(res[2].devices[0].web_id, "Zep33-e")
        self.assertEqual(res[2].devices[0].location, "echo")
        self.assertEqual(res[2].devices[1].device_id, "Zep22")
        self.assertEqual(res[2].devices[1].web_id, "Zep22-f")
        self.assertEqual(res[2].devices[1].location, "frank")

    def test_missing_device(self):
        # Have asked for a device that doesn't exist in the Device definition
        devs = ["FOO182", "AQM18", "AQY81", "Zep22", "Zep33"]
        res = setup_manufacturers(deepcopy(self.valid_config), devs)
        self.assertEqual(len(res), 3)
        self.assertEqual(len(res[0].devices), 1)
        self.assertEqual(len(res[1].devices), 1)
        self.assertEqual(len(res[2].devices), 2)
        self.assertEqual(res[0].devices[0].device_id, "AQY81")
        self.assertEqual(res[0].devices[0].web_id, "AQY81-b")
        self.assertEqual(res[0].devices[0].location, "bar")
        self.assertEqual(res[1].devices[0].device_id, "AQM18")
        self.assertEqual(res[1].devices[0].web_id, "AQM18-c")
        self.assertEqual(res[1].devices[0].location, "cat")
        self.assertEqual(res[2].devices[0].device_id, "Zep33")
        self.assertEqual(res[2].devices[0].web_id, "Zep33-e")
        self.assertEqual(res[2].devices[0].location, "echo")
        self.assertEqual(res[2].devices[1].device_id, "Zep22")
        self.assertEqual(res[2].devices[1].web_id, "Zep22-f")
        self.assertEqual(res[2].devices[1].location, "frank")

    def test_json_no_manufacturer_list(self):
        # If there isn't a list of 'manufacturer' objects in the dict, then nothing
        # should be created.
        # Here have a dict, rather than a list
        invalid_config = {
            "Aeroqual": {"devices": ["a", "b", "c"]},
            "AQMesh": {"devices": ["a", "b", "c"]},
            "Zephyr": {"devices": ["a", "b", "c"]},
        }
        devs = ["FOO182", "AQM18", "AQY81", "Zep22", "Zep33"]
        res = setup_manufacturers(invalid_config, devs)
        self.assertEqual(len(res), 0)

    def test_json_no_manufacturer_list2(self):
        # If there isn't a list of 'manufacturer' objects in the dict, then nothing
        # should be created.
        # Here have a list of lists
        invalid_config = [["Aeroqual", "AQMesh"]]
        devs = ["FOO182", "AQM18", "AQY81", "Zep22", "Zep33"]
        res = setup_manufacturers(invalid_config, devs)
        self.assertEqual(len(res), 0)

    def test_json_no_manufacturer_list3(self):
        # If there isn't a list of 'manufacturer' objects in the dict, then nothing
        # should be created.
        # Here have a list of dicts, but the name attribute isn't present,
        # instead we're using 'id' for 2 of the manufacturers
        invalid_config = [
            {
                "id": "Aeroqual",
                "properties": defaultdict(str),
                "fields": [],
                "devices": [
                    {"id": "AQY10", "webid": "AQY10-a", "location": "foo"},
                    {"id": "AQY81", "webid": "AQY81-b", "location": "bar"},
                ],
            },
            {
                "name": "AQMesh",
                "properties": defaultdict(str),
                "fields": [],
                "devices": [
                    {"id": "AQM18", "webid": "AQM18-c", "location": "cat"},
                    {"id": "AQM99", "webid": "AQM99-d", "location": "dog"},
                ],
            },
            {
                "id": "Zephyr",
                "properties": defaultdict(str),
                "fields": [],
                "devices": [
                    {"id": "Zep33", "webid": "Zep33-e", "location": "echo"},
                    {"id": "Zep22", "webid": "Zep22-f", "location": "frank"},
                ],
            },
        ]
        devs = ["FOO182", "AQM18", "AQY81", "Zep22", "Zep33"]
        res = setup_manufacturers(invalid_config, devs)
        self.assertEqual(len(res), 1)
        self.assertEqual(len(res[0].devices), 1)
        self.assertEqual(res[0].devices[0].device_id, "AQM18")
        self.assertEqual(res[0].devices[0].web_id, "AQM18-c")
        self.assertEqual(res[0].devices[0].location, "cat")

    def test_empty_device_list(self):
        # Have asked for a device that doesn't exist in the Device definition
        devs = []
        res = setup_manufacturers(deepcopy(self.valid_config), devs)
        self.assertEqual(len(res), 0)

    def test_mispelt_manufacturer(self):
        # Have misspelt AQMesh, so that this manufacturer and its associated
        # devices shouldn't be included in the output
        invalid_config = [
            {
                "name": "Aeroqual",
                "properties": defaultdict(str),
                "fields": [],
                "devices": [
                    {"id": "AQY10", "webid": "AQY10-a", "location": "foo"},
                    {"id": "AQY81", "webid": "AQY81-b", "location": "bar"},
                ],
            },
            {
                "name": "AQmesh",
                "properties": defaultdict(str),
                "fields": [],
                "devices": [
                    {"id": "AQM18", "webid": "AQM18-c", "location": "cat"},
                    {"id": "AQM99", "webid": "AQM99-d", "location": "dog"},
                ],
            },
            {
                "name": "Zephyr",
                "properties": defaultdict(str),
                "fields": [],
                "devices": [
                    {"id": "Zep33", "webid": "Zep33-e", "location": "echo"},
                    {"id": "Zep22", "webid": "Zep22-f", "location": "frank"},
                ],
            },
        ]
        devs = ["AQM18", "AQY81", "Zep22", "Zep33"]
        res = setup_manufacturers(invalid_config, devs)
        self.assertEqual(len(res), 2)
        self.assertEqual(len(res[0].devices), 1)
        self.assertEqual(len(res[1].devices), 2)
        self.assertEqual(res[0].devices[0].device_id, "AQY81")
        self.assertEqual(res[0].devices[0].web_id, "AQY81-b")
        self.assertEqual(res[0].devices[0].location, "bar")
        self.assertEqual(res[1].devices[0].device_id, "Zep33")
        self.assertEqual(res[1].devices[0].web_id, "Zep33-e")
        self.assertEqual(res[1].devices[0].location, "echo")
        self.assertEqual(res[1].devices[1].device_id, "Zep22")
        self.assertEqual(res[1].devices[1].web_id, "Zep22-f")
        self.assertEqual(res[1].devices[1].location, "frank")
