"""
    test_save_data.py
    ~~~~~~~~~~~~~~~~~

    Unit tests for methods that save data: cli.save_data(),
    utils.save_csv_file() and utils.save_json_file().
"""

import unittest
import configparser
import string
from unittest.mock import patch, Mock, call, mock_open
import pandas as pd
import quantscraper.manufacturers.Aeroqual as Aeroqual
import quantscraper.utils as utils
import quantscraper.cli as cli


class TestSaveCSVFile(unittest.TestCase):
    # The saving clean data functionality is split into 2 functions:
    #    - cli.save_data: iterates through all devices, forms their
    #          filename and extracts their clean data
    #    - utils.save_csv_file: Does actual writing to file of a given CSV
    #          dataset and a given filename.

    # This class tests the latter.

    def test_success(self):
        m = mock_open()

        # Save file to specified folder with filename template:
        with patch("quantscraper.utils.open", m):
            # Need to patch os.path to force file to not exist
            with patch("quantscraper.utils.os.path") as mock_path:
                mock_path.isfile = Mock(return_value=False)
                # patch CSV and mock csv.writer
                with patch("quantscraper.utils.csv") as mock_csv:
                    mock_writer = Mock()
                    mock_writerows = Mock()
                    mock_writer.return_value = Mock(writerows=mock_writerows)
                    mock_csv.writer = mock_writer

                    utils.save_csv_file([[1, 2, 3], [4, 5, 6]], "path/to/fn.csv")
                    # Check calls are as expected
                    m.assert_called_once_with("path/to/fn.csv", "w")
                    mock_writer.assert_called_once_with(m(), delimiter=",")
                    mock_writerows.assert_called_once_with([[1, 2, 3], [4, 5, 6]])

    def test_file_exists(self):
        # Check that the DataSavingError is raised when file exists
        m = mock_open()

        with patch("quantscraper.utils.open", m):
            # Mock file existing
            with patch("quantscraper.utils.os.path") as mock_path:
                mock_path.isfile = Mock(return_value=True)

                with self.assertRaises(utils.DataSavingError):
                    utils.save_csv_file([[1, 2, 3], [4, 5, 6]], "path/to/fn.csv")

    def test_dir_doesnt_exist(self):
        m = mock_open()
        # open raises FileNotFoundError if dir doesn't exist
        m.side_effect = FileNotFoundError()

        # Save file to specified folder with filename template:
        with patch("quantscraper.utils.open", m):
            # Need to patch os.path to force file to not exist
            with patch("quantscraper.utils.os.path") as mock_path:
                mock_path.isfile = Mock(return_value=False)
                # patch CSV and mock csv.writer
                with patch("quantscraper.utils.csv") as mock_csv:
                    mock_writer = Mock()
                    mock_writerows = Mock()
                    mock_writer.return_value = Mock(writerows=mock_writerows)
                    mock_csv.writer = mock_writer

                    with self.assertRaises(utils.DataSavingError):
                        utils.save_csv_file([[1, 2, 3], [4, 5, 6]], "path/to/fn.csv")


class TestSaveCleanData(unittest.TestCase):
    # The saving clean data functionality is split into 2 functions:
    #    - cli.save_data: iterates through all devices, forms their
    #          filename and extracts their clean data
    #    - utils.save_csv_file: Does actual writing to file of a given CSV
    #          dataset and a given filename.

    # This class tests the former.

    cfg = configparser.ConfigParser()
    cfg.read("example.ini")

    # Set dummy device properties
    cfg.set("Aeroqual", "devices", "1,2")
    cfg.set("Aeroqual", "devices_web", "1,2")
    cfg.set("Aeroqual", "device_locations", "foo,foo")

    def test_success(self):
        aeroqual = Aeroqual.Aeroqual(self.cfg)
        # Set dummy data
        aeroqual._clean_data = {"1": [[1, 2, 3], [4, 5, 6]], "2": [[7, 8, 9]]}

        # Need to patch os.path to force directory to exist
        with patch("quantscraper.cli.os.path.isdir") as mock_isdir:
            mock_isdir.return_value = True

            # patch actual function that saves
            with patch("quantscraper.utils.save_csv_file") as mock_save:

                try:
                    res = cli.save_data(aeroqual, "dummyFolder", "foobar", "clean")

                    calls = mock_save.mock_calls
                    exp_calls = [
                        call(
                            [[1, 2, 3], [4, 5, 6]], "dummyFolder/Aeroqual_1_foobar.csv",
                        ),
                        call([[7, 8, 9]], "dummyFolder/Aeroqual_2_foobar.csv"),
                    ]
                    self.assertEqual(calls, exp_calls)
                    # Function should output names of files that are
                    # successfully saved
                    self.assertEqual(
                        res,
                        [
                            "dummyFolder/Aeroqual_1_foobar.csv",
                            "dummyFolder/Aeroqual_2_foobar.csv",
                        ],
                    )
                except:
                    self.fail("Test raised error when should have passed.")

    def test_dir_doesnt_exist(self):
        aeroqual = Aeroqual.Aeroqual(self.cfg)
        # Set dummy data
        aeroqual._clean_data = {"1": [[1, 2, 3], [4, 5, 6]], "2": [[7, 8, 9]]}

        # Need to patch os.path to force directory to not exist
        with patch("quantscraper.cli.os.path.isdir") as mock_isdir:
            mock_isdir.return_value = False

            with patch("quantscraper.utils.save_csv_file") as mock_save:

                with self.assertRaises(utils.DataSavingError):
                    cli.save_data(aeroqual, "dummyFolder", "startT", "clean")

    def test_success_None_data(self):
        # in case a dataset for a device is None, then shouldn't attempt to save
        aeroqual = Aeroqual.Aeroqual(self.cfg)
        # Set dummy data
        aeroqual._clean_data = {"1": [[1, 2, 3], [4, 5, 6]], "2": None}

        # Need to patch os.path to force directory to exist
        with patch("quantscraper.cli.os.path.isdir") as mock_isdir:
            mock_isdir.return_value = True

            # patch actual function that saves
            with patch("quantscraper.utils.save_csv_file") as mock_save:

                try:
                    res = cli.save_data(aeroqual, "dummyFolder", "today", "clean")

                    # This inner function should only be called once on account
                    # of second device not having data
                    mock_save.assert_called_once_with(
                        [[1, 2, 3], [4, 5, 6]], "dummyFolder/Aeroqual_1_today.csv"
                    )
                    # Function should only return filename from first file that
                    # saved successfully
                    self.assertEqual(res, ["dummyFolder/Aeroqual_1_today.csv"])
                except:
                    self.fail("Test raised error when should have passed.")

    def test_error_saving_file(self):
        # First file saves successfully but second fails as that filename
        # already exists
        aeroqual = Aeroqual.Aeroqual(self.cfg)
        # Set dummy data
        aeroqual._clean_data = {"1": [[1, 2, 3], [4, 5, 6]], "2": [[7, 8, 9]]}

        # Need to patch os.path to force directory to exist
        with patch("quantscraper.cli.os.path.isdir") as mock_isdir:
            mock_isdir.return_value = True

            # patch actual function that saves
            with patch("quantscraper.utils.save_csv_file") as mock_save:
                mock_save.side_effect = ["", utils.DataSavingError("")]

                try:
                    res = cli.save_data(aeroqual, "dummyFolder", "foobar", "clean")

                    calls = mock_save.mock_calls
                    exp_calls = [
                        call(
                            [[1, 2, 3], [4, 5, 6]], "dummyFolder/Aeroqual_1_foobar.csv",
                        ),
                        call([[7, 8, 9]], "dummyFolder/Aeroqual_2_foobar.csv"),
                    ]
                    self.assertEqual(calls, exp_calls)
                    # Should only have first filename returned
                    self.assertEqual(res, ["dummyFolder/Aeroqual_1_foobar.csv"])
                except:
                    self.fail("Test raised error when should have passed.")


class TestSaveJSONFile(unittest.TestCase):
    # The saving raw data functionality is split into 2 functions:
    #    - cli.save_data: iterates through all devices, forms their
    #          filename and extracts their clean data
    #    - utils.save_json_file: Does actual writing to file of a given
    #          serializable Python object and a given filename.

    # This class tests the latter.

    def test_success(self):
        m = mock_open()

        # Save file to specified folder with filename template:
        with patch("quantscraper.utils.open", m):
            # Need to patch os.path to force file to not exist
            with patch("quantscraper.utils.os.path") as mock_path:
                mock_path.isfile = Mock(return_value=False)
                # patch json
                with patch("quantscraper.utils.json") as mock_json:
                    mock_dump = Mock()
                    mock_json.dump = mock_dump

                    utils.save_json_file([[1, 2, 3], [4, 5, 6]], "path/to/fn.json")
                    # Check calls are as expected
                    m.assert_called_once_with("path/to/fn.json", "w")
                    mock_dump.assert_called_once_with([[1, 2, 3], [4, 5, 6]], m())

    def test_file_exists(self):
        # Check that the DataSavingError is raised when file exists
        m = mock_open()

        with patch("quantscraper.utils.open", m):
            # Mock file existing
            with patch("quantscraper.utils.os.path") as mock_path:
                mock_path.isfile = Mock(return_value=True)

                with self.assertRaises(utils.DataSavingError):
                    utils.save_json_file([[1, 2, 3], [4, 5, 6]], "path/to/fn.json")

    def test_dir_doesnt_exist(self):
        # Check that the DataSavingError is raised when dir doesn't exist,
        # which raises a FileNotFoundError
        m = mock_open()
        m.side_effect = FileNotFoundError()

        with patch("quantscraper.utils.open", m):
            # Mock file existing
            with patch("quantscraper.utils.os.path") as mock_path:
                mock_path.isfile = Mock(return_value=True)

                with self.assertRaises(utils.DataSavingError):
                    utils.save_json_file([[1, 2, 3], [4, 5, 6]], "path/to/fn.json")

    # Unfortunately can't mock JSONDecodeError to assert this error is handled
    # correctly, as the error needs to be instantiated which I can't mock.


class TestSaveRawData(unittest.TestCase):
    # The saving raw data functionality is split into 2 functions:
    #    - cli.save_data: iterates through all devices, forms their
    #          filename and extracts their clean data
    #    - utils.save_json_file: Does actual writing to file of a given
    #          serializable Python object and a given filename.

    # This class tests the former.
    cfg = configparser.ConfigParser()
    cfg.read("example.ini")

    # Set dummy device properties
    cfg.set("Aeroqual", "devices", "1,2")
    cfg.set("Aeroqual", "devices_web", "1,2")
    cfg.set("Aeroqual", "device_locations", "foo,foo")

    def test_success(self):
        aeroqual = Aeroqual.Aeroqual(self.cfg)
        # Set dummy data
        aeroqual._raw_data = {"1": [[1, 2, 3], [4, 5, 6]], "2": [[7, 8, 9]]}

        # Need to patch os.path to force directory to exist
        with patch("quantscraper.utils.os.path.isdir") as mock_isdir:
            mock_isdir.return_value = True

            # patch actual function that saves
            with patch("quantscraper.utils.save_json_file") as mock_save:

                try:
                    res = cli.save_data(aeroqual, "dummyFolder", "day", "raw")

                    calls = mock_save.mock_calls
                    exp_calls = [
                        call(
                            [[1, 2, 3], [4, 5, 6]], "dummyFolder/Aeroqual_1_day.json",
                        ),
                        call([[7, 8, 9]], "dummyFolder/Aeroqual_2_day.json"),
                    ]
                    self.assertEqual(calls, exp_calls)
                    # should return both filenames as saved successfully
                    self.assertEqual(
                        res,
                        [
                            "dummyFolder/Aeroqual_1_day.json",
                            "dummyFolder/Aeroqual_2_day.json",
                        ],
                    )
                except:
                    self.fail("Test raised error when should have passed.")

    def test_dir_doesnt_exist(self):
        aeroqual = Aeroqual.Aeroqual(self.cfg)
        # Set dummy data
        aeroqual._raw_data = {"1": [[1, 2, 3], [4, 5, 6]], "2": [[7, 8, 9]]}

        # Need to patch os.path to force directory to not exist
        with patch("quantscraper.cli.os.path.isdir") as mock_isdir:
            mock_isdir.return_value = False

            with patch("quantscraper.utils.save_json_file") as mock_save:

                with self.assertRaises(utils.DataSavingError):
                    cli.save_data(aeroqual, "dummyFolder", "foobar", "raw")

    def test_success_None_data(self):
        # in case a dataset for a device is None, then shouldn't attempt to save
        aeroqual = Aeroqual.Aeroqual(self.cfg)
        # Set dummy data
        aeroqual._raw_data = {"1": [[1, 2, 3], [4, 5, 6]], "2": None}

        # Need to patch os.path to force directory to exist
        with patch("quantscraper.cli.os.path.isdir") as mock_isdir:
            mock_isdir.return_value = True

            # patch actual function that saves
            with patch("quantscraper.utils.save_json_file") as mock_save:

                try:
                    res = cli.save_data(aeroqual, "dummyFolder", "day", "raw")

                    # This inner function should only be called once on account
                    # of second device not having data
                    mock_save.assert_called_once_with(
                        [[1, 2, 3], [4, 5, 6]], "dummyFolder/Aeroqual_1_day.json",
                    )
                    # should return both filenames as saved successfully
                    self.assertEqual(res, ["dummyFolder/Aeroqual_1_day.json"])
                except:
                    self.fail("Test raised error when should have passed.")

    def test_error_saving_file(self):
        # First file saves successfully but second fails as that filename
        # already exists
        aeroqual = Aeroqual.Aeroqual(self.cfg)
        # Set dummy data
        aeroqual._raw_data = {"1": [[1, 2, 3], [4, 5, 6]], "2": [[7, 8, 9]]}

        # Need to patch os.path to force directory to exist
        with patch("quantscraper.cli.os.path.isdir") as mock_isdir:
            mock_isdir.return_value = True

            # patch actual function that saves
            with patch("quantscraper.utils.save_json_file") as mock_save:
                mock_save.side_effect = ["", utils.DataSavingError("")]

                try:
                    res = cli.save_data(aeroqual, "dummyFolder", "foobar", "raw")

                    calls = mock_save.mock_calls
                    exp_calls = [
                        call(
                            [[1, 2, 3], [4, 5, 6]],
                            "dummyFolder/Aeroqual_1_foobar.json",
                        ),
                        call([[7, 8, 9]], "dummyFolder/Aeroqual_2_foobar.json"),
                    ]
                    self.assertEqual(calls, exp_calls)
                    # Should only have first filename returned
                    self.assertEqual(res, ["dummyFolder/Aeroqual_1_foobar.json"])
                except:
                    self.fail("Test raised error when should have passed.")


class TestSaveDataFrame(unittest.TestCase):
    # Tests utils.save_dataframe function that writes a pandas.DataFrame to disk
    def test_success(self):
        dummy_data = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        # Need to patch os.path to force file to not exist
        with patch("quantscraper.utils.os.path") as mock_path:
            mock_path.isfile = Mock(return_value=False)
            with patch.object(pd.DataFrame, "to_csv") as mock_to_csv:
                utils.save_dataframe(dummy_data, "path/to/fn.csv")
                # Check calls is as expected
                mock_to_csv.assert_called_once_with("path/to/fn.csv")

    def test_file_exists(self):
        dummy_data = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        # Check that the DataSavingError is raised when file exists
        with patch("quantscraper.utils.os.path") as mock_path:
            mock_path.isfile = Mock(return_value=True)

            with self.assertRaises(utils.DataSavingError):
                utils.save_dataframe(dummy_data, "path/to/fn.csv")

    def test_dir_doesnt_exist(self):
        # If dir doesn't exist a FileNotFoundError is raised
        dummy_data = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
        # Need to patch os.path to force file to not exist
        with patch("quantscraper.utils.os.path") as mock_path:
            mock_path.isfile = Mock(return_value=False)
            with patch.object(pd.DataFrame, "to_csv") as mock_to_csv:
                mock_to_csv.side_effect = FileNotFoundError()

                with self.assertRaises(utils.DataSavingError):
                    utils.save_dataframe(dummy_data, "path/to/fn.csv")


class TestSavePlaintext(unittest.TestCase):
    # Tests utils.save_plaintext function that writes a string to disk
    def test_success(self):
        m = mock_open()
        mock_write = Mock()
        mock_outfile = Mock(write=mock_write)

        dummy_text = "foobar\ncar"

        # Save file to specified folder with filename template:
        with patch("quantscraper.utils.open", m):
            # Need to patch os.path to force file to not exist
            with patch("quantscraper.utils.os.path") as mock_path:
                mock_path.isfile = Mock(return_value=False)

                utils.save_plaintext(dummy_text, "path/to/fn.txt")
                # Check calls are as expected
                m.assert_called_once_with("path/to/fn.txt", "w")

    def test_file_exists(self):
        # Check that the DataSavingError is raised when file exists
        m = mock_open()
        dummy_text = "foobar\ncar"
        with patch("quantscraper.utils.open", m):
            # Mock file existing
            with patch("quantscraper.utils.os.path") as mock_path:
                mock_path.isfile = Mock(return_value=True)

                with self.assertRaises(utils.DataSavingError):
                    utils.save_plaintext(dummy_text, "path/to/fn.txt")

    def test_dir_doesnt_exist(self):
        m = mock_open()
        # open raises FileNotFoundError if dir doesn't exist
        m.side_effect = FileNotFoundError()
        dummy_text = "foobar\ncar"

        # Save file to specified folder with filename template:
        with patch("quantscraper.utils.open", m):
            # Need to patch os.path to force file to not exist
            with patch("quantscraper.utils.os.path") as mock_path:
                mock_path.isfile = Mock(return_value=False)
                with self.assertRaises(utils.DataSavingError):
                    utils.save_plaintext(dummy_text, "path/to/fn.txt")


class TestLoadHTMLTemplate(unittest.TestCase):
    # Tests that utils.load_html_tempate() can load file
    def test_success(self):
        m = mock_open(read_data="foo")

        # Save file to specified folder with filename template:
        with patch("quantscraper.utils.open", m):

            res = utils.load_html_template("path/to/fn.txt")
            # Check calls are as expected
            m.assert_called_once_with("path/to/fn.txt", "r")
            # Assert return value is a template and has the appropriate value
            self.assertIsInstance(res, string.Template)
            self.assertEqual(res.substitute(), "foo")

    def test_success_with_placeholder(self):
        m = mock_open(read_data="foo = $value")

        # Save file to specified folder with filename template:
        with patch("quantscraper.utils.open", m):

            res = utils.load_html_template("path/to/fn.txt")
            # Check calls are as expected
            m.assert_called_once_with("path/to/fn.txt", "r")
            # Assert return value is a template and has the appropriate value
            self.assertIsInstance(res, string.Template)
            self.assertEqual(res.substitute(value=5), "foo = 5")

    def test_file_doesnt_exist(self):
        # Check that the DataReadingError is raised when file doesn't exist
        m = mock_open()
        m.side_effect = FileNotFoundError("")
        with patch("quantscraper.utils.open", m):
            with self.assertRaises(utils.DataReadingError):
                utils.load_html_template("path/to/fn.txt")

    def test_io_error(self):
        # Check that the DataReadingError is raised when generic IOError is
        # encountered
        m = mock_open()
        m.side_effect = IOError("")
        with patch("quantscraper.utils.open", m):
            with self.assertRaises(utils.DataReadingError):
                utils.load_html_template("path/to/fn.txt")

    # Template() parses any string, which is what file.read() returns,
    # so can't test that the template is correctly formatted here


if __name__ == "__main__":
    unittest.main()
