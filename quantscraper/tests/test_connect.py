"""
    test_connect.py
    ~~~~~~~~~~~~~~~

    Unit tests for Manufacturer.connect() methods.
"""

import unittest
import quantscraper

# Test that returns True when correct credentials are passed in
# Test that returns False when incorrect credentials are passed in
#   - correct username but incorrect password
#   - correct password but incorrect username
#   - correct credentials but wrong URL / headers
# Test that returns False when network issue (can temporarily disable Wifi, but
# how to automate this?)

# Test correct error messages are displayed? Or is this reponsibility of cli
# script?

# Can have one class for each test, with each method targeting a different
# manufacturer


class TestCorrectCredentials(unittest.TestCase):
    # Read in config
    pass


if __name__ == "__main__":
    unittest.main()
