import csv
import json
import os
import logging
import traceback
from string import Template
from abc import ABC, abstractmethod, abstractproperty
import requests as re
from quantscraper.utils import DataDownloadError, DataSavingError, DataParseError


class Manufacturer(ABC):
    # Unsure how to force Name as an abstract class property.
    # Can only get it working as an instance attribute

    @property
    def clean_data(self):
        """
        TODO
        """
        return self._clean_data

    @clean_data.setter
    # TODO Clean this up as currently doesn't work: 
        # can only have 1 non-self argument. Can pass a dict mapping 
        # {devID: value} as second argument
    def clean_data(self, devID, value):
        """
        TODO
        """
        self._clean_data[devID] = value

    @property
    def raw_data(self):
        """
        TODO
        """
        return self._raw_data

    @raw_data.setter
    def raw_data(self, devID, value):
        """
        TODO
        """
        self._raw_data[devID] = value

    @abstractmethod
    def scrape_device(self, deviceID):
        """
        TODO
        """
        pass

    @abstractmethod
    def parse_to_csv(self, rawdata):
        """
        TODO
        """
        pass

    def __init__(self, cfg):
        """
        Sets up object with parameters needed to scrape data.

        Args:
            - cfg: Instance of ConfigParser

        Returns:
            None
        """
        self._raw_data = {}
        self._clean_data = {}

    @abstractmethod
    def connect(self):
        """
        TODO
        """

    def scrape(self):
        """
        TODO
        """
        # TODO Should this code be here, or should it be in the CLI script, so
        # that all logging is run in once place?
        for devid in self.device_ids:
            try:
                logging.info("Attempting to scrape data for device {}...".format(devid))
                self.raw_data[devid] = self.scrape_device(devid)
                logging.info("Scrape successful.")
            except DataDownloadError as ex:
                logging.error("Unable to download data for device {}.".format(devid))
                logging.error(traceback.format_exc())
                self.raw_data[devid] = None

    # TODO Better name?! preprocess? process_data?
    def process(self):
        """
        TODO
        """
        # TODO Like with scrape(), should this code below be handled in the CLI
        # script? Is it fair for Manufacturer (a library class) to access
        # logger?
        for devid in self.device_ids:

            logging.info("Cleaning data from device {}...".format(devid))
            if self.raw_data[devid] is None:
                logging.warning("No available raw data")
                self.clean_data[devid] = None
                continue

            try:
                logging.info("Attempting to parse data into CSV...")
                self.clean_data[devid] = self.parse_to_csv(self.raw_data[devid])
                logging.info(
                    "Parse successful. {} samples have been recorded.".format(
                        len(self.clean_data[devid])
                    )
                )
            except DataParseError as ex:
                logging.error("Unable to parse data into CSV for device {}.".format(devid))
                logging.error(traceback.format_exc())
                self.clean_data[devid] = None
                continue
                
            # TODO Implement! And raise custom exception
            logging.info("Running validation...".format(devid))
            self.clean_data[devid] = self.validate_data(self.clean_data[devid])
            logging.info(
                "Validation successful. There are {} samples with no errors.".format(
                    len(self.clean_data[devid])
                )
            )

    def validate_data(self, data):
        """
        Runs QA validation checks on air quality data.
        
        Args:
            data (list): Data in CSV, i.e. a 2D list, format. 
                It will likely be stored as strings.

        Returns:
            The cleaned data, in the same 2D list structure.
        """
        return data

    def save_clean_data(self, folder, start_time, end_time):
        """
        Iterates through all its devices and saves their cleaned data to disk.

        Uses the following template filename:

        <manufacturer_name>_<deviceid>_<start_timeframe>_<end_timeframe>.csv

        Args:
            - folder (str): Directory where files should be saved to.
            - start_time (str): Starting time of scraping window. In same
                string format as INI file uses.
            - end_time (str): End time of scraping window. In same
                string format as INI file uses.

        Returns:
            None. Saves data to disk as CSV files as a side-effect.
        """
        # TODO Change start + end time to just a single date, as this is primary
        # usecase?

        if not os.path.isdir(folder):
            raise DataSavingError(
                "Folder {} doesn't exist, cannot save clean data.".format(folder)
            )

        filename = Template("${man}_${device}_${start}_${end}.csv")
        for devid in self.device_ids:
            fn = filename.substitute(
                man=self.name, device=devid, start=start_time, end=end_time
            )

            data = self.clean_data[devid]
            if data is None:
                logging.warning(
                    "No clean data to save for device {}.".format(devid)
                )
                continue

            full_path = os.path.join(folder, fn)
            logging.info("Saving data to file: {}".format(full_path))
            self._save_clean_data(full_path, data)

    def _save_clean_data(self, filename, data):
        """
        Actual function that saves data.

        Uses the following template filename:

        Args:
            - filename (str): Location to save data to
            - data (list): Data in CSV (2D list) format to be saved.

        Returns:
            None. Saves data to disk as CSV files as a side-effect.
        """
        if os.path.isfile(filename):
            raise DataSavingError("File {} already exists.".format(filename))

        with open(filename, "w") as outfile:
            writer = csv.writer(outfile, delimiter=",")
            writer.writerows(data)

    # TODO How best to refactor this? Same functionality as save_clean_data but
    # different data source and different output.
    # So this function does same logic (generate filename in same format,
    # iterate through devices), only difference is whether uses .clean_data or
    # .raw_data
    # the helper function _save_raw_data does the same job as _save_clean_data
    # but it saves to JSON rather than CSV
    def save_raw_data(self, folder, start_time, end_time):
        """
        Iterates through all its devices and saves their raw data to disk.

        Uses the following template filename:

        <manufacturer_name>_<deviceid>_<start_timeframe>_<end_timeframe>.csv

        Args:
            - folder (str): Directory where files should be saved to.
            - start_time (str): Starting time of scraping window. In same
                string format as INI file uses.
            - end_time (str): End time of scraping window. In same
                string format as INI file uses.

        Returns:
            None. Saves data to disk as CSV files as a side-effect.
        """
        # TODO Change start + end time to just a single date, as this is primary
        # usecase?

        if not os.path.isdir(folder):
            raise DataSavingError(
                "Folder {} doesn't exist, cannot save raw data.".format(folder)
            )

        filename = Template("${man}_${device}_${start}_${end}.json")
        for devid in self.device_ids:
            fn = filename.substitute(
                man=self.name, device=devid, start=start_time, end=end_time
            )

            data = self.raw_data[devid]
            if data is None:
                logging.warning(
                    "No raw data to save for device {}.".format(devid)
                )
                continue

            full_path = os.path.join(folder, fn)
            logging.info("Saving data to file: {}".format(full_path))
            self._save_raw_data(full_path, data)

    def _save_raw_data(self, filename, data):
        """
        Actual function that saves data.

        Uses the following template filename:

        Args:
            - filename (str): Location to save data to
            - data (misc): Data in JSON-parseable format.

        Returns:
            None. Saves data to disk as JSON files as a side-effect.
        """
        if os.path.isfile(filename):
            raise DataSavingError("File {} already exists.".format(filename))

        try:
            with open(filename, "w") as outfile:
                json.dump(data, outfile)
        except json.decoder.JSONDecodeError:
            raise DataSavingError(
                "Unable to serialize raw data to json."
            )
    # TODO Need to document device_ids parameter as abstract
