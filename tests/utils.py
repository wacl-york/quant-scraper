"""
    tests/utils.py
    ~~~~~~~~~~~~~~

    Utility functions for unit tests.
"""
from unittest.mock import Mock
import datetime


def build_mock_today(year, month, day):
    class MockDate(datetime.date):
        @classmethod
        def today(cls):
            return cls(year, month, day)

    return MockDate


def build_mock_response(
    status=200, content="CONTENT", json_data=None, raise_for_status=None, text=None,
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
    return mock_resp
