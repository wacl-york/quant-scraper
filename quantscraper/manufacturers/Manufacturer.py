import logging
import math
import traceback
from abc import ABC, abstractmethod, abstractproperty
import requests as re
from datetime import datetime
import quantscraper.utils as utils

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
            except utils.DataDownloadError as ex:
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
            except utils.DataParseError as ex:
                logging.error("Unable to parse data into CSV for device {}.".format(devid))
                logging.error(traceback.format_exc())
                self.clean_data[devid] = None
                continue
                
            logging.info("Running validation...".format(devid))
            try:
                self.clean_data[devid] = self.validate_data(self.clean_data[devid])
                logging.info(
                    "Validation successful. There are {} samples with no errors.".format(
                        len(self.clean_data[devid])
                    )
                )
            except utils.ValidateDataError:
                logging.error("Something went wrong during data validation.")
                self.clean_data[devid] = None


    def validate_data(self, data):
        """
        Runs QA validation checks on air quality data.
        
        Args:
            data (list): Data in CSV, i.e. a 2D list, format. 
                It will likely be stored as strings.

        Returns:
            The cleaned data, in the same 2D list structure.
        """
        if data is None:
            raise utils.ValidateDataError(
                "Input data is None."
            )

        if len(data) == 0:
            raise utils.ValidateDataError(
                "0 errors in input data."
            )

        # Output timestamp format
        output_format = "%Y-%m-%d %H:%M:%S"
        nrows = len(data)
        measurand_indices = {}
        timestamp_index = None
        
        # First row should be header so obtain numeric indices
        for i, col in enumerate(data[0]):
            if col == self.timestamp_col:
                timestamp_index = i
            elif col in self.cols_to_validate:
                measurand_indices[col] = i
            else:
                continue

        if timestamp_index is None:
            raise utils.ValidateDataError(
                "No timestamp column '{}' found.".format(self.timestamp_col)
            )

        available_measurands = list(measurand_indices.keys())

        # Store counts of number of clean values
        n_clean_vals = {k: 0 for k in available_measurands}
        n_clean_vals['timestamp'] = 0
        # List to store clean data in
        clean_data = [['timestamp', 'measurand', 'value']]

        # Start at 1 to skip header
        for i in range(1, nrows):
            row = data[i]
            try:
                dt = datetime.strptime(row[timestamp_index], self.timestamp_format)
            except ValueError:
                continue

            n_clean_vals['timestamp'] += 1
            timestamp_clean = dt.strftime(output_format)

            for measurand in available_measurands:
                val_raw = row[measurand_indices[measurand]]

                if not utils.is_float(val_raw):
                    continue
                
                n_clean_vals[measurand] += 1
                clean_row = [timestamp_clean, measurand, float(val_raw)]
                clean_data.append(clean_row)

        summary = utils.summarise_validation(len(data)-1, n_clean_vals)
        logging.info(summary)

        return clean_data


    # TODO Need to document device_ids parameter as abstract
