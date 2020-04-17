"""
    manufacturer_factory.py
    ~~~~~~~~~~~~~~~~~~~~~~~

    Builds instances of Manufacturer sub-classes.
"""

from quantscraper.manufacturers.Aeroqual import Aeroqual
from quantscraper.manufacturers.AQMesh import AQMesh
from quantscraper.manufacturers.Zephyr import Zephyr
from quantscraper.manufacturers.MyQuantAQ import MyQuantAQ


def manufacturer_factory(option, config):
    """
    Returns an instance of the specified Manufacturer sub-class.

    Args:
        - option (str): The string name of the Manufacturer sub-class.
        - config (configparser.Namespace): Configuration options used to
            instantiate the Manufacturer sub-class.

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
        cls = factory[option]
    except KeyError:
        raise KeyError(
            "No Manufacturer '{}', available options are {}.".format(
                option, list(factory.keys())
            )
        ) from None

    return cls(config)
