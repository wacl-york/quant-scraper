import requests as re
from abc import ABC, abstractmethod, abstractproperty


class Manufacturer(ABC):
    @abstractproperty
    def name(self):
        """
        Manufacturer name, as used as a section in the config file.
        """
        pass

    @abstractproperty
    def clean_data(self):
        """
        TODO
        """
        pass

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
    def __init__(self, cfg):
        """
        Sets up object with parameters needed to scrape data.

        Args:
            - cfg: Instance of ConfigParser

        Returns:
            None
        """
        self._raw_data = {}
        self.connect()

    def connect(self):
        """
        TODO
        """
        self.session = re.Session()
        result = self.session.post(
            self.auth_url, data=self.auth_params, headers=self.auth_headers
        )
        print("auth response: " + str(result))
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

    @abstractmethod
    def scrape_device(self, deviceID):
        """
        TODO
        """
        pass
