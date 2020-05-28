"""
    factories.py
    ~~~~~~~~~~~~

    Builds instances of Manufacturer and Device classes.
"""

import logging
from quantscraper.manufacturers.Aeroqual import Aeroqual
from quantscraper.manufacturers.AQMesh import AQMesh
from quantscraper.manufacturers.Zephyr import Zephyr
from quantscraper.manufacturers.MyQuantAQ import MyQuantAQ
from quantscraper.manufacturers.Manufacturer import Device


def manufacturer_factory(config):
    """
    Returns an instance of the specified Manufacturer sub-class.

    Args:
        - cfg (dict): Attributes of the manufacturer, given by the corresponding
            object containing the 'name', 'fields', 'devices' etc... attributes
            in the devices JSON file.

    Returns:
        An instance of the specified Manufacturer sub-class.
    """
    factory = {
        "Aeroqual": Aeroqual,
        "AQMesh": AQMesh,
        "Zephyr": Zephyr,
        "QuantAQ": MyQuantAQ,
    }
    try:
        option = config["name"]
    except (KeyError, TypeError):
        raise KeyError("No 'name' attribute in manufacturer config.") from None

    try:
        cls = factory[option]
    except KeyError:
        raise KeyError(
            "No Manufacturer '{}', available options are {}.".format(
                option, list(factory.keys())
            )
        ) from None

    try:
        inst = cls(config["properties"], config["fields"])
    except KeyError as ex:
        raise KeyError("Cannot instantiate {}: {}".format(option, ex)) from None

    return inst


def device_factory(config):
    """
    Returns an instance of the specified Manufacturer sub-class.

    Args:
        - config (configparser.Namespace): Configuration options used to
            instantiate the Device. These are the properties inside a 'devices'
            list in the JSON.
            Must contain at least:
                - id
                - webid
                - location
    Returns:
        A Device instance.
    """
    try:
        id = config["id"]
        config.pop("id")
        webid = config["webid"]
        config.pop("webid")
        location = config["location"]
        config.pop("location")
        dev = Device(id, webid, location, **config)
    except KeyError:
        raise KeyError(
            "Each device must have at least 'id', 'webid', and 'location' fields."
        )

    return dev


def setup_manufacturers(manufacturer_config, device_list=None):
    """
    Instanties Manufacturer and specified Device objects.

    The Manufacturer and Device properties used to populate these classes
    are defined in a JSON object that must be passed into this function

    Args:
        - manufacturer_config (dict): A list of dicts that define the
            manufacturers in our study. Corresponds to the 'manufacturers' list in
            the devices JSON file.
        - device_list (str[], optional): A list of strings giving the device names to be
            instantiated. If not supplied, then all the devices in
            manufacturer_config are loaded.

    Returns:
        A list of Manufacturer objects, each of which is populated with the
        chosen Devices.
    """
    manufacturers = []
    for man_dict in manufacturer_config:
        try:
            man_inst = manufacturer_factory(man_dict)
        except KeyError as ex:
            logging.error("Cannot instantiate Manufacturer from config: {}".format(ex))
            logging.error("Manufacturer configuration: {}".format(man_dict))
            continue

        try:
            devices = man_dict["devices"]
        except KeyError:
            logging.error(
                "No 'devices' attribute in manufacturer config for {}.".format(
                    man_dict["name"]
                )
            )
            continue

        for device_dict in devices:

            try:
                dev_id = device_dict["id"]
            except KeyError:
                logging.error(
                    "Device configuration has no 'id' attribute: {}".format(device_dict)
                )
                continue

            if device_list is not None and not dev_id in device_list:
                continue

            device_inst = device_factory(device_dict)
            man_inst.add_device(device_inst)

        if len(man_inst.devices) > 0:
            manufacturers.append(man_inst)

    return manufacturers
