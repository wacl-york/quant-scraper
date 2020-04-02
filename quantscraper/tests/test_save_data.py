"""
    test_save_data.py
    ~~~~~~~~~~~~~~~~~

    Unit tests for methods that save data: Manufacturer.save_raw_data() and
    Manufacturer.save_clean_data().
"""

import unittest
import configparser
from string import Template
from unittest.mock import patch, MagicMock, Mock, call, mock_open
from requests.exceptions import Timeout, HTTPError
from quantaq.baseapi import DataReadError
import quantscraper.manufacturers.Manufacturer as Manufacturer
import quantscraper.manufacturers.Aeroqual as Aeroqual
import quantscraper.manufacturers.AQMesh as AQMesh
import quantscraper.manufacturers.Zephyr as Zephyr
import quantscraper.manufacturers.MyQuantAQ as MyQuantAQ
from quantscraper.utils import DataSavingError
from quantscraper.tests.test_utils import build_mock_response

class Test_SaveCleanData(unittest.TestCase):
    # I've refactored the saving clean data functionality into 2 functions:
    #    - save_clean_data: iterates through all devices, forms their
    #          filename and extracts their clean data
    #    - _save_clean_data: Does actual writing to file of a given CSV
    #          dataset and a given filename.

    # This class tests the latter.

    # Manufacturer._save_clean_data() is a concrete method so don't need to test
    # each subclass's implementation, but as Manufacturer has some abstract
    # methods and thus can't be instantiated, need to use a subclass to use for testing

    cfg = configparser.ConfigParser()
    cfg.read("example.ini")

    def test_success(self):
        aeroqual = Aeroqual.Aeroqual(self.cfg)
        m = mock_open()

        # Save file to specified folder with filename template:
        with patch("quantscraper.manufacturers.Manufacturer.open", m):
            # Need to patch os.path to force file to not exist
            with patch("quantscraper.manufacturers.Manufacturer.os.path") as mock_path:
                mock_path.isfile = Mock(return_value=False)
                # patch CSV and mock csv.writer
                with patch("quantscraper.manufacturers.Manufacturer.csv") as mock_csv:
                    mock_writer = Mock()
                    mock_writerows = Mock()
                    mock_writer.return_value = Mock(writerows = mock_writerows)
                    mock_csv.writer = mock_writer

                    aeroqual._save_clean_data("path/to/fn.csv", [[1, 2, 3], [4, 5,
                                                                             6]])

                    # Check calls are as expected
                    m.assert_called_once_with("path/to/fn.csv", 'w')
                    mock_writer.assert_called_once_with(m(), delimiter=",")
                    mock_writerows.assert_called_once_with([[1, 2, 3], [4, 5, 6]])

    def test_file_exists(self):
        # Check that the DataSavingError is raised when file exists
        aeroqual = Aeroqual.Aeroqual(self.cfg)
        m = mock_open()

        with patch("quantscraper.manufacturers.Manufacturer.open", m):
            # Mock file existing
            with patch("quantscraper.manufacturers.Manufacturer.os.path") as mock_path:
                mock_path.isfile = Mock(return_value=True)

                with self.assertRaises(DataSavingError):
                    aeroqual._save_clean_data("path/to/fn.csv", [[1, 2, 3], [4, 5,
                                                                             6]])


class TestSaveCleanData(unittest.TestCase):
    # I've refactored the saving clean data functionality into 2 functions:
    #    - save_clean_data: iterates through all devices, forms their
    #          filename and extracts their clean data
    #    - _save_clean_data: Does actual writing to file of a given CSV
    #          dataset and a given filename.

    # This class tests the former.
    # It iterates through each device and generates the filename as:
    # "${manufacturer}_${device}_${start}_${end}.csv"
    # And pulls the clean data, then calls _save_clean_data to do the writing

    # Manufacturer.save_clean_data() is a concrete method so don't need to test
    # each subclass's implementation, but as Manufacturer has some abstract
    # methods and thus can't be instantiated, need to use a subclass to use for testing

    cfg = configparser.ConfigParser()
    cfg.read("example.ini")

    # Set dummy device IDs
    cfg.set('Aeroqual', 'devices', '1,2')

    def test_success(self):
        aeroqual = Aeroqual.Aeroqual(self.cfg)
        # Set dummy data
        aeroqual._clean_data = {'1': [[1, 2, 3], [4, 5, 6]],
                                '2': [[7, 8, 9]]
                               }

        # Need to patch os.path to force directory to exist
        with patch("quantscraper.manufacturers.Manufacturer.os.path.isdir") as mock_isdir:
            mock_isdir.return_value = True

            # patch actual function that saves
            with patch("quantscraper.manufacturers.Manufacturer.Manufacturer._save_clean_data") as mock_save:

                try:
                    aeroqual.save_clean_data("dummyFolder", "startT", "endT")

                    calls = mock_save.mock_calls
                    exp_calls = [
                                 call("dummyFolder/Aeroqual_1_startT_endT.csv",
                                       [[1, 2, 3], [4, 5, 6]]
                                      ),
                                 call("dummyFolder/Aeroqual_2_startT_endT.csv",
                                       [[7, 8, 9]]
                                     )
                                 ]
                    self.assertEqual(calls, exp_calls)
                    print(mock_isdir.mock_calls)
                except:
                    self.fail("Test raised error when should have passed.")

    def test_dir_doesnt_exist(self):
        aeroqual = Aeroqual.Aeroqual(self.cfg)
        # Set dummy data
        aeroqual._clean_data = {'1': [[1, 2, 3], [4, 5, 6]],
                                '2': [[7, 8, 9]]
                               }

        # Need to patch os.path to force directory to not exist
        with patch("quantscraper.manufacturers.Manufacturer.os.path.isdir") as mock_isdir:
            mock_isdir.return_value = False

            with patch("quantscraper.manufacturers.Manufacturer.Manufacturer._save_clean_data") as mock_save:

                with self.assertRaises(DataSavingError):
                        aeroqual.save_clean_data("dummyFolder", "startT", "endT")

    def test_success_None_data(self):
        # in case a dataset for a device is None, then shouldn't attempt to save
        aeroqual = Aeroqual.Aeroqual(self.cfg)
        # Set dummy data
        aeroqual._clean_data = {'1': [[1, 2, 3], [4, 5, 6]],
                                '2': None
                               }

        # Need to patch os.path to force directory to exist
        with patch("quantscraper.manufacturers.Manufacturer.os.path.isdir") as mock_isdir:
            mock_isdir.return_value = True

            # patch actual function that saves
            with patch("quantscraper.manufacturers.Manufacturer.Manufacturer._save_clean_data") as mock_save:

                try:
                    aeroqual.save_clean_data("dummyFolder", "startT", "endT")
                    
                    # This inner function should only be called once on account
                    # of second device not having data
                    mock_save.assert_called_once_with("dummyFolder/Aeroqual_1_startT_endT.csv",
                                                      [[1, 2, 3], [4, 5, 6]])
                except:
                    self.fail("Test raised error when should have passed.")


class Test_SaveRawData(unittest.TestCase):
    # I've refactored the saving raw data functionality into 2 functions:
    #    - save_raw_data: iterates through all devices, forms their
    #          filename and extracts their raw data
    #    - _save_raw: Does actual writing to file of a given
    #          dataset and a given filename.

    # This class tests the latter.

    # Manufacturer._save_raw_data() is a concrete method so don't need to test
    # each subclass's implementation, but as Manufacturer has some abstract
    # methods and thus can't be instantiated, need to use a subclass to use for testing

    cfg = configparser.ConfigParser()
    cfg.read("example.ini")

    def test_success(self):
        aeroqual = Aeroqual.Aeroqual(self.cfg)
        m = mock_open()

        # Save file to specified folder with filename template:
        with patch("quantscraper.manufacturers.Manufacturer.open", m):
            # Need to patch os.path to force file to not exist
            with patch("quantscraper.manufacturers.Manufacturer.os.path") as mock_path:
                mock_path.isfile = Mock(return_value=False)
                # patch json
                with patch("quantscraper.manufacturers.Manufacturer.json") as mock_json:
                    mock_dump = Mock()
                    mock_json.dump = mock_dump

                    aeroqual._save_raw_data("path/to/fn.json", [[1, 2, 3], [4, 5,
                                                                             6]])

                    # Check calls are as expected
                    m.assert_called_once_with("path/to/fn.json", 'w')
                    mock_dump.assert_called_once_with([[1, 2, 3], [4, 5, 6]], m())

    def test_file_exists(self):
        # Check that the DataSavingError is raised when file exists
        aeroqual = Aeroqual.Aeroqual(self.cfg)
        m = mock_open()

        with patch("quantscraper.manufacturers.Manufacturer.open", m):
            # Mock file existing
            with patch("quantscraper.manufacturers.Manufacturer.os.path") as mock_path:
                mock_path.isfile = Mock(return_value=True)

                with self.assertRaises(DataSavingError):
                    aeroqual._save_raw_data("path/to/fn.json", [[1, 2, 3], [4, 5,
                                                                             6]])


class TestSaveRawData(unittest.TestCase):
    # I've refactored the saving raw data functionality into 2 functions:
    #    - save_raw_data: iterates through all devices, forms their
    #          filename and extracts their raw data
    #    - _save_raw_data: Does actual writing to file of a given
    #          dataset and a given filename.

    # This class tests the former.
    # It iterates through each device and generates the filename as:
    # "${manufacturer}_${device}_${start}_${end}.json"
    # And pulls the raw data, then calls _save_raw_data to do the writing

    # Manufacturer.save_raw_data() is a concrete method so don't need to test
    # each subclass's implementation, but as Manufacturer has some abstract
    # methods and thus can't be instantiated, need to use a subclass to use for testing

    cfg = configparser.ConfigParser()
    cfg.read("example.ini")

    # Set dummy device IDs
    cfg.set('Aeroqual', 'devices', '1,2')

    def test_success(self):
        aeroqual = Aeroqual.Aeroqual(self.cfg)
        # Set dummy data
        aeroqual._raw_data = {'1': [[1, 2, 3], [4, 5, 6]],
                                '2': [[7, 8, 9]]
                               }

        # Need to patch os.path to force directory to exist
        with patch("quantscraper.manufacturers.Manufacturer.os.path.isdir") as mock_isdir:
            mock_isdir.return_value = True

            # patch actual function that saves
            with patch("quantscraper.manufacturers.Manufacturer.Manufacturer._save_raw_data") as mock_save:

                try:
                    aeroqual.save_raw_data("dummyFolder", "startT", "endT")

                    calls = mock_save.mock_calls
                    exp_calls = [
                                 call("dummyFolder/Aeroqual_1_startT_endT.json",
                                       [[1, 2, 3], [4, 5, 6]]
                                      ),
                                 call("dummyFolder/Aeroqual_2_startT_endT.json",
                                       [[7, 8, 9]]
                                     )
                                 ]
                    self.assertEqual(calls, exp_calls)
                    print(mock_isdir.mock_calls)
                except:
                    self.fail("Test raised error when should have passed.")

    def test_dir_doesnt_exist(self):
        aeroqual = Aeroqual.Aeroqual(self.cfg)
        # Set dummy data
        aeroqual._raw_data = {'1': [[1, 2, 3], [4, 5, 6]],
                                '2': [[7, 8, 9]]
                               }

        # Need to patch os.path to force directory to not exist
        with patch("quantscraper.manufacturers.Manufacturer.os.path.isdir") as mock_isdir:
            mock_isdir.return_value = False

            with patch("quantscraper.manufacturers.Manufacturer.Manufacturer._save_raw_data") as mock_save:

                with self.assertRaises(DataSavingError):
                        aeroqual.save_raw_data("dummyFolder", "startT", "endT")

    def test_success_None_data(self):
        # in case a dataset for a device is None, then shouldn't attempt to save
        aeroqual = Aeroqual.Aeroqual(self.cfg)
        # Set dummy data
        aeroqual._raw_data = {'1': [[1, 2, 3], [4, 5, 6]],
                                '2': None
                               }

        # Need to patch os.path to force directory to exist
        with patch("quantscraper.manufacturers.Manufacturer.os.path.isdir") as mock_isdir:
            mock_isdir.return_value = True

            # patch actual function that saves
            with patch("quantscraper.manufacturers.Manufacturer.Manufacturer._save_raw_data") as mock_save:

                try:
                    aeroqual.save_raw_data("dummyFolder", "startT", "endT")
                    
                    # This inner function should only be called once on account
                    # of second device not having data
                    mock_save.assert_called_once_with("dummyFolder/Aeroqual_1_startT_endT.json",
                                                      [[1, 2, 3], [4, 5, 6]])
                except:
                    self.fail("Test raised error when should have passed.")


if __name__ == "__main__":
    unittest.main()
