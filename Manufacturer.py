import csv
import os
from string import Template
from abc import ABC, abstractmethod, abstractproperty
import requests as re


class Manufacturer(ABC):
    @abstractproperty
    def name(self):
        """
        Manufacturer name, as used as a section in the config file.
        """
        pass

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
        self.connect()

    # TODO Should this be super implementation, or just copy the exact same
    # method for both the Aeroqual and AQMesh subclasses? These 2 manufacturers
    # use this method, but the other 2 have their own instance. Given that would
    # need to have session, auth_headers, auth_params, auth_url as all abstract
    # attrs, maybe should just make an abstract connect() method and copy paste
    # this implementation twice
    def connect(self):
        """
        TODO
        """
        self.session = re.Session()
        result = self.session.post(
            self.auth_url, data=self.auth_params, headers=self.auth_headers
        )
        if result.status_code != re.codes["ok"]:
            # TODO convert to log
            print("Error: cannot connect")
            return False
        else:
            return True

    def scrape(self):
        """
        TODO
        """
        for devid in self.device_ids:
            self.raw_data[devid] = self.scrape_device(devid)

    def process_data(self):
        """
        TODO
        """
        for devid in self.device_ids:
            if self.raw_data[devid] is None:
                print("No available raw data for device {}.".format(devid))
                continue
            self.clean_data[devid] = self.process_device(devid)

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
            print("Folder {} doesn't exist, cannot save clean data.".format(folder))
        else:
            filename = Template("${man}_${device}_${start}_${end}.csv")
            for devid in self.device_ids:
                fn = filename.substitute(
                    man=self.name, device=devid, start=start_time, end=end_time
                )

                data = self.clean_data[devid]
                if data is None:
                    print("No clean data to save for device {}.".format(devid))
                    continue

                # TODO Add more error handling (what exceptions to look out
                # for?)
                with open(os.path.join(folder, fn), "w") as outfile:
                    writer = csv.writer(outfile, delimiter=",")
                    writer.writerows(data)

    # TODO Need to document device_ids parameter as abstract
