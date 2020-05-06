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

import numpy as np
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
        - devices (str[]): A list of human readable IDs for its devices.
        - devices_web (str[]): A list of IDs for its devices as used by the
            corresponding website for scraping data.
        - device_locations (str[]): A list of recording locations for each device,
            used for providing context in the output log.
        - raw_data (dict(JSON)): The raw data from the devices. The keys of the
            dict are the IDs stored in 'devices', and the entries are the
            corresponding raw data saved in a JSON-serializable format, as returned
            from the download.
        - clean_data (dict(2D list)): The clean data from the devices. The keys of the
            dict are the IDs stored in 'devices', and the entries are the
            corresponding cleaned and validated data in a long CSV format, with
            3 columns:
                - timestamp (str)
                - measurand (str)
                - value (float)
            The first entry in the list contains the column header labels with data
            stored in all subsequent entries.

    Methods:
        - __init__: Constructor that reads in the configuration object and sets
            appropriate instance attributes.
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
    def device_ids(self):
        """
        A list of human readable IDs for the devices, stored as a
        list of strings.
        """
        return self._device_ids

    @property
    def device_web_ids(self):
        """
        A list of IDs for its devices as used by the website for scraping data,
        stored as a list of strings.
        """
        return self._device_web_ids

    @property
    def device_locations(self):
        """
        A list of recording locations for each device,
        stored as a list of strings.
        """
        return self._device_locations

    @property
    def raw_data(self):
        """
        The raw data from the devices stored as JSON inside a dict().

        The keys of the dict are the IDs stored in 'devices', and the entries are the
        corresponding raw data saved in a JSON-serializable format, as returned
        from the download.
        """
        return self._raw_data

    @property
    def clean_data(self):
        """
         The cleaned and validated data from the devices stored as a 2D list
         inside a dict().

         The keys of the dict are the IDs stored in 'devices', and the entries
         are the corresponding cleaned and validated data in a long CSV format,
         with 3 columns:
                - timestamp (str)
                - measurand (str)
                - value (float)

        The first entry in the list contains the column header labels with data
        stored in all subsequent entries.
        """
        return self._clean_data

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
    def scrape_device(self, device_id):
        """
        Downloads the data for a given device.

        The scraping timeframe, along with other manufacturer-specific
        parameters are stored in the .ini configuration file and set in the
        constructor as instance attributes if needed.

        Abstract method that must have a concrete implementation provided by
        sub-classes.

        Args:
            device_id (str): The website device_id to scrape for.

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

    def __init__(self, cfg):
        """
        Sets up object with parameters needed to scrape data.

        Args:
            - cfg (configparser.Namespace): Instance of ConfigParser.

        Returns:
            None, sets many instance attributes.
        """
        self._raw_data = {}
        self._clean_data = {}

        self._device_ids = cfg.get(self.name, "devices").split(",")
        self._device_web_ids = cfg.get(self.name, "devices_web").split(",")
        self._device_locations = cfg.get(self.name, "device_locations").split(",")
        self._recording_frequency = cfg.getfloat(
            self.name, "recording_frequency_per_hour"
        )
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

        # Ensure have the same number of values for device properties
        lengths = [
            len(self.device_ids),
            len(self.device_web_ids),
            len(self.device_locations),
        ]
        if len(set(lengths)) != 1:
            raise utils.DataParseError(
                "Options 'devices', 'devices_web' and 'device_locations' must have the same number of entries."
            )

        # Ensure have the same number of values for column properties
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
            }
            self.measurands.append(entry)

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
        requested_measurands_raw = [r["raw_label"] for r in self.measurands]
        requested_measurands_clean = [r["clean_label"] for r in self.measurands]

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
