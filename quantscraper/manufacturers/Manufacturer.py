"""
    quantscraper.manufacturers.Manufacturer.py
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    Contains the abstract base class for Manufacturer instances, which represent
    a Manufacturer of air quality sensors. Each manufacturer has a number of
    Devices which hold raw measurement data.
    Each sub-class contains routines for downloading data for their devices and
    parsing this raw JSON data into a common CSV format.

    The base class also provides an implemented method that validates the
    resultant CSV data, by identifying values that are parseable as numerical
    data.
"""

from abc import ABC, abstractmethod
from datetime import datetime
import quantscraper.utils as utils


class Manufacturer(ABC):
    """
    The abstract base class for Manufacturer.

    Attributes:
        - name (str, abstract): A human readable name for the manufacturer.
        - recording_frequency (double): Expected recording frequency of all
            devices from this manufacturer,
        measured as number of measurements an hour.
        - devices (Device[]): A list of Device objects that are owned by this
            manufacturer.

    Methods:
        - __init__: Constructor that reads in the configuration object and sets
            appropriate instance attributes.
        - add_device: Adds a Device object to the Manufacturer's 'devices' list.
        - connect (abstract): Establishes a connection to the manufacturer's
            website and handles any required authentication.
        - scrape_device (abstract): Downloads the data for a given device.
        - parse_to_csv (abstract): Parses a device's raw JSON data into a
            tabular 2D list format.
        - validate_data: Runs QA validation checks on air quality data.
    """

    # Name is both abstract and a class method
    @property
    @classmethod
    @abstractmethod
    def name(cls):
        """
        A human readable name for the manufacturer as a string.
        """

    @property
    def recording_frequency(self):
        """
        Expected recording frequency of all devices from this manufacturer,
        measured as number of measurements an hour.
        """
        return self._recording_frequency

    @property
    def devices(self):
        """
        A list of Devices representing the physical instrumentation devices
        owned by this company.
        """
        return self._devices

    @abstractmethod
    def connect(self):
        """
        Establishes a connection to the manufacturer's website and handles any
        required authentication.

        Abstract method that must have a concrete implementation provided by
        sub-classes.

        Args:
            - None

        Returns:
            None, although often sets an instance attribute providing a handle
            to an authenticated connection.
        """

    @abstractmethod
    def scrape_device(self, device_id, start, end):
        """
        Downloads the data for a given device.

        The scraping timeframe, along with other manufacturer-specific
        parameters are stored in the .ini configuration file and set in the
        constructor as instance attributes if needed.

        Abstract method that must have a concrete implementation provided by
        sub-classes.

        Args:
            - device_id (str): The ID used by the website to refer to the
                device.
            - start (date): The start of the scraping window.
            - end (date): The end of the scraping window.

        Returns:
            A JSON serializable object holding the raw data.
        """

    @abstractmethod
    def parse_to_csv(self, raw_data):
        """
        Parses a device's raw JSON data into a tabular 2D list format.

        Abstract method that must have a concrete implementation provided by
        sub-classes.

        Args:
            - raw_data (JSON serializable): Raw data for a device, in the same
                format as returned by scrape_device().

        Returns:
            A 2D list representing the data in a tabular format, so that each
            row corresponds to a unique time-point and each column holds a
            measurand.
        """

    def __init__(self, cfg, fields):
        """
        Sets up object with parameters needed to scrape data.

        Args:
            - cfg (dict): Keyword-argument properties set in the Manufacturer's
                'properties' attribute.
            - fields (list): List of dicts detailing the measurands available
                for this manufacturer and their properties.

        Returns:
            None, sets many instance attributes.
        """
        self._devices = []

        self._recording_frequency = cfg["recording_frequency_per_hour"]
        # Name of column that holds timestamp
        self.timestamp_col = cfg["timestamp_column"]
        # String providing the format of the timestamp
        self.timestamp_format = cfg["timestamp_format"]
        # Information about measurands parsed by this manufacturer
        self.measurands = fields

    def add_device(self, device):
        """
        Adds a Device object to the Manufacturer's 'devices' list.

        Args:
            - device (Device): New device to be added.

        Returns:
            None, populates the 'devices' attribute as a side-effect.
        """
        self._devices.append(device)

    def validate_data(self, data):
        """
        Runs QA validation checks on air quality data.

        It isn't ideal having this function return a tuple of the clean data and
        the validation summary dict, but it works for now.

        Args:
            data (2D list): Data in the CSV format as returned by parse_to_csv.
                The values themselves will still be stored as strings.

        Returns:
            A tuple with:
                - The cleaned data in a long CSV format, with
                    3 columns:
                        - timestamp (str)
                        - measurand (str)
                        - value (float)
                    The first entry in the list contains the column header labels with data
                    stored in all subsequent entries.
                - A dictionary mapping {measurand: # clean samples}
        """
        # Requested measurands in the raw label used by manufacturer and clean
        # human-readable label
        requested_measurands_raw = [r["webid"] for r in self.measurands]
        requested_measurands_clean = [r["id"] for r in self.measurands]

        # Store counts of number of clean values
        n_clean_vals = {k: 0 for k in requested_measurands_clean}
        n_clean_vals["timestamp"] = 0
        # List to store clean data in
        clean_data = [["timestamp", "measurand", "value"]]

        if data is None:
            raise utils.ValidateDataError("Input data is None.")

        if len(data) == 0:
            raise utils.ValidateDataError("0 rows in input data.")

        # Remove duplicate rows. Set obtains unique values but only runs on
        # hashable datatypes, such as tuples, rather than lists
        header = data[0]
        data_vals = [list(t) for t in set(tuple(element) for element in data[0:])]
        data_vals.insert(0, header)
        data = data_vals

        # TODO put desired output timestamp format in config?
        output_format = "%Y-%m-%d %H:%M:%S"
        nrows = len(data)
        measurand_indices = {}
        scaling_factors = {}
        timestamp_index = None

        # First row should be header so obtain numeric indices
        for i, col in enumerate(data[0]):
            if col == self.timestamp_col:
                timestamp_index = i
            elif col in requested_measurands_raw:
                # Store this index under the clean measurand label
                measurand_index = requested_measurands_raw.index(col)
                clean_label = self.measurands[measurand_index]["id"]
                measurand_indices[clean_label] = i
                scaling_factors[clean_label] = self.measurands[measurand_index]["scale"]
            else:
                continue

        if timestamp_index is None:
            raise utils.ValidateDataError(
                "No timestamp column '{}' found.".format(self.timestamp_col)
            )

        available_measurands = list(measurand_indices.keys())

        # Start at 1 to skip header
        for i in range(1, nrows):
            row = data[i]

            # See if timestamp is in valid format
            try:
                timestamp_dt = datetime.strptime(
                    row[timestamp_index], self.timestamp_format
                )
            except ValueError:
                continue
            n_clean_vals["timestamp"] += 1
            timestamp_clean = timestamp_dt.strftime(output_format)

            # See if can parse each measurand as float
            for measurand in available_measurands:
                val_raw = row[measurand_indices[measurand]]

                if not utils.is_float(val_raw):
                    continue

                # Scale by the appropriate factor
                val_scaled = float(val_raw) * scaling_factors[measurand]

                n_clean_vals[measurand] += 1
                clean_row = [timestamp_clean, measurand, val_scaled]
                clean_data.append(clean_row)

        return clean_data, n_clean_vals


class Device:
    """
    Represents a physical instrumentation device that records air quality data.

    Attributes:
        - device_id (str): A human readable ID used to refer to this device.
        - web_id (str): An ID used by the device manufacturer to refer to the
            device.
        - location (str): A label describing where the device is located.
        - Any other key-value properties are set from the device's JSON
            description.
        - raw_data (JSON): The raw data saved in a JSON-serializable format,
            as returned from the download.
        - clean_data (2D list): The cleaned and validated data in a long CSV
            format, with 3 columns:
                - timestamp (str)
                - measurand (str)
                - value (float)
            The first entry in the list contains the column header labels with data
            stored in all subsequent entries.

    Methods:
        None.
    """

    @property
    def raw_data(self):
        """
        The raw data from the device stored as JSON.

        The raw data is stored in a JSON-serializable format, as returned
        directly from the download.
        """
        return self._raw_data

    @raw_data.setter
    def raw_data(self, val):
        """
        Sets the raw_data field.
        """
        self._raw_data = val

    @property
    def clean_data(self):
        """
         The cleaned and validated data from the device. stored as a 2D list.

         The data is organised in a long CSV format with 3 columns:
                - timestamp (str)
                - measurand (str)
                - value (float)

        The first entry in the list contains the column header labels with data
        stored in all subsequent entries.
        """
        return self._clean_data

    @clean_data.setter
    def clean_data(self, val):
        """
        Sets the clean_data field.
        """
        self._clean_data = val

    def __init__(self, id, webid, location, **kwargs):
        """
        Constructor.

        Args:
            - id (str): A human readable ID used to refer to this device.
            - web_id (str): An ID used by the device manufacturer to refer to the
                device.
            - location (str): A label describing where the device is located.
            - kwargs (dict): Any other properties relevant to this device, that
                are set as instance attributes.

        Returns:
            A new Device instance.
        """
        self.device_id = id
        self.web_id = webid
        self.location = location
        self._raw_data = None
        self._clean_data = None

        # Set any additional properties
        for k, v in kwargs.items():
            setattr(self, k, v)
