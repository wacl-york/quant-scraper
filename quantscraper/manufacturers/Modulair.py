"""
    quantscraper.manufacturers.Modulair.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Subclass of MyQuantAQ, representing the Modulair air
    quality instrumentation device manufacturer.

    Modulair's devices are accessed through the same QuantAQ API as the QuantAQ
    devices, but have been separated into a different namespace to differentiate
    between them.
    Also, there are some slight differences between the names of columns
    returned.
"""

from quantscraper.manufacturers.MyQuantAQ import MyQuantAQ


class Modulair(MyQuantAQ):
    """
    Inherits attributes and methods from MyQuantAQ.
    """

    name = "QuantAQ"
