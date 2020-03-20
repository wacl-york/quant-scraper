import requests as re
from abc import ABC, abstractmethod, abstractproperty


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

    def process_data(self):
        """
        TODO
        """
        for devid in self.device_ids:
            self.clean_data[devid] = self.process_device(devid)


# TODO Need to document device_ids parameter as abstract
