"""
    test_cli.py
    ~~~~~~~~~~~

    Unit tests for cli functions.
"""

import unittest
import quantscraper

# Test parse_args:
#    - is this needed? Is it possible to test CLI arguments through unit testing?
#    - more appropriate to keep parse_args() as a function and make a
#    parse_config() function, that:
#       - has args filepath, and returns config object
#       - it also performs basic QA, ensuring the filepath exists and the INI is
#       formatted correctly
#   - can then test this parse_config() function

# Test setup_scraping_timeline:
#   - how to test this automatically? requires knowing yesterday's date, which
#     is obviously dependent upon the date the test is run. To generate expected
#     outputs, I would end up rewriting the same logic that the function uses.
#     Thereby defeating point of testing

# Test setup_loggers:
#   Not essential for now
#   But can test format
