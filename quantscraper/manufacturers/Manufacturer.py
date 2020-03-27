import csv
import os
import logging
from string import Template
from abc import ABC, abstractmethod, abstractproperty
import requests as re


class Manufacturer(ABC):
    # Unsure how to force Name as an abstract class property.
    # Can only get it working as an instance attribute

    @property
    def clean_data(self):
        """
        TODO
        """
        return self._raw_data

    @clean_data.setter
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
    def process_device(self, deviceID):
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
        for devid in self.device_ids:
            logging.info("Attempting to scrape data for device {}...".format(devid))
            self.raw_data[devid] = self.scrape_device(devid)
            logging.info("Scrape successful.")

    def parse_to_csv(self):
        """
        TODO
        """
        for devid in self.device_ids:
            if self.raw_data[devid] is None:
                logging.warning("No available raw data for device {}.".format(devid))
                continue
            logging.info(
                "Attempting to parse data into CSV for device {}...".format(devid)
            )
            self.clean_data[devid] = self.process_device(devid)
            logging.info(
                "Parse successful. {} samples have been recorded.".format(
                    len(self.clean_data[devid])
                )
            )

    def save_clean_data(self, folder, start_time, end_time):
        """
        Saves clean data to file.

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
            logging.error(
                "Folder {} doesn't exist, cannot save clean data.".format(folder)
            )
        else:
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

                # TODO Add more error handling (what exceptions to look out
                # for?)
                full_path = os.path.join(folder, fn)
                logging.info("Saving data to file: {}".format(full_path))
                with open(full_path, "w") as outfile:
                    writer = csv.writer(outfile, delimiter=",")
                    writer.writerows(data)

    # TODO Need to document device_ids parameter as abstract
