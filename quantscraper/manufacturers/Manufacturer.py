import logging
import math
import traceback
from abc import ABC, abstractmethod, abstractproperty
import requests as re
from datetime import datetime
import quantscraper.utils as utils


class Manufacturer(ABC):

    # Name is both abstract and a class method
    @property
    @classmethod
    @abstractmethod
    def name(self):
        pass

    @property
    def devices(self):
        return self._devices

    @property
    def devices_web(self):
        return self._devices_web

    @property
    def clean_data(self):
        """
        TODO
        """
        return self._clean_data

    @property
    def raw_data(self):
        """
        TODO
        """
        return self._raw_data

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
        self.device_ids = cfg.get(self.name, "devices").split(",")
        self.device_web_ids = cfg.get(self.name, "devices_web").split(",")
        # Name of column that holds timestamp
        self.timestamp_col = cfg.get(self.name, "timestamp_column")
        # String providing the format of the timestamp
        self.timestamp_format = cfg.get(self.name, "timestamp_format")

        # Setup the measurand metadata, so have a record of which measurands to
        # expect in raw data, what labels to reassign them, and if they need
        # scaling at all. Store all this in a list of dicts
        cols = cfg.get(self.name, "columns_to_validate").split(",")
        labels = cfg.get(self.name, "column_labels").split(",")
        scales = cfg.get(self.name, "scaling_factors").split(",")
        analysis = cfg.get(self.name, "columns_to_preprocess").split(",")

        # Ensure have the same number of values
        lengths = [len(cols), len(labels), len(scales)]
        if len(set(lengths)) != 1:
            raise utils.DataParseError(
                "Options 'columns_to_validate', 'column_labels' and 'scaling_factors' must have the same number of entries."
            )

        self.measurands = []
        for i in range(lengths[0]):
            scaling_factor = scales[i]
            if not utils.is_float(scaling_factor):
                scaling_factor = 1
            else:
                scaling_factor = float(scaling_factor)
            entry = {
                "raw_label": cols[i],
                "clean_label": labels[i],
                "scale": scaling_factor,
                "included_analysis": labels[i] in analysis,
            }
            self.measurands.append(entry)

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
        for webid, devid in zip(self.device_web_ids, self.device_ids):
            try:
                logging.info("Attempting to scrape data for device {}...".format(webid))
                self.raw_data[devid] = self.scrape_device(webid)
                logging.info("Scrape successful.")
            except utils.DataDownloadError as ex:
                logging.error("Unable to download data for device {}.".format(webid))
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
                logging.error(
                    "Unable to parse data into CSV for device {}.".format(devid)
                )
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
        validate_cols = [r["raw_label"] for r in self.measurands]

        if data is None:
            raise utils.ValidateDataError("Input data is None.")

        if len(data) == 0:
            raise utils.ValidateDataError("0 errors in input data.")

        # TODO put desired output timestamp format in config
        output_format = "%Y-%m-%d %H:%M:%S"
        nrows = len(data)
        measurand_indices = {}
        scaling_factors = {}
        timestamp_index = None

        # First row should be header so obtain numeric indices
        for i, col in enumerate(data[0]):
            if col == self.timestamp_col:
                timestamp_index = i
            elif col in validate_cols:
                # Store this index under the clean measurand label
                measurand_index = validate_cols.index(col)
                clean_label = self.measurands[measurand_index]["clean_label"]
                measurand_indices[clean_label] = i
                scaling_factors[clean_label] = self.measurands[measurand_index]["scale"]
            else:
                continue

        if timestamp_index is None:
            raise utils.ValidateDataError(
                "No timestamp column '{}' found.".format(self.timestamp_col)
            )

        available_measurands = list(measurand_indices.keys())

        # Store counts of number of clean values
        n_clean_vals = {k: 0 for k in available_measurands}
        n_clean_vals["timestamp"] = 0
        # List to store clean data in
        clean_data = [["timestamp", "measurand", "value"]]

        # Start at 1 to skip header
        for i in range(1, nrows):
            row = data[i]
            try:
                dt = datetime.strptime(row[timestamp_index], self.timestamp_format)
            except ValueError:
                continue

            n_clean_vals["timestamp"] += 1
            timestamp_clean = dt.strftime(output_format)

            for measurand in available_measurands:
                val_raw = row[measurand_indices[measurand]]

                if not utils.is_float(val_raw):
                    continue

                val_scaled = float(val_raw) * scaling_factors[measurand]

                n_clean_vals[measurand] += 1
                clean_row = [timestamp_clean, measurand, val_scaled]
                clean_data.append(clean_row)

        summary = utils.summarise_validation(len(data) - 1, n_clean_vals)
        logging.info(summary)

        return clean_data
