#!/usr/bin/env python3
"""
    cli.py
    ~~~~~~

    Main scraper script that collects data from each of the four manufacturers.
    By default it obtains all data from midnight to the following midnight of
    the previous day.  This behaviour can be changed in the config.ini file,
    which is also where credentials are stored.
"""

import logging
import argparse
import os
import sys
import json
import math
import configparser
import re
from datetime import date, timedelta, datetime, time
import traceback
from dotenv import load_dotenv

import quantscraper.utils as utils
from quantscraper.factories import setup_manufacturers

CONFIG_FN = "config.ini"
DEVICES_FN = "devices.json"


def setup_loggers(logfn=None):
    """
    Configures loggers.

    By default, the error log is printed to standard out,
    although it can be saved to file in addition.

    Args:
        - logfn (str, optional): File to save log to. If None then doesn't write log to file.

    Returns:
        None. the logger is accessed by the global module `logging`.
    """
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    log_fmt = logging.Formatter(
        "%(asctime)-8s:%(levelname)s: %(message)s", datefmt="%Y-%m-%d,%H:%M:%S"
    )
    cli_logger = logging.StreamHandler()
    cli_logger.setFormatter(log_fmt)
    root_logger.addHandler(cli_logger)

    if not logfn is None:
        if os.path.isfile(logfn):
            raise utils.SetupError(
                ("Log file {} already exists. " "Halting execution.").format(logfn)
            )
        file_logger = logging.FileHandler(logfn)
        file_logger.setFormatter(log_fmt)
        root_logger.addHandler(file_logger)


def parse_args():
    """
    Parses CLI arguments to the script.

    Args:
        - None

    Returns:
        An argparse.Namespace object.
    """
    parser = argparse.ArgumentParser(description="QUANT scraper")
    parser.add_argument(
        "--devices",
        metavar="DEVICES",
        nargs="+",
        help="Specify the device IDs to include in the scraping. If not provided then all the devices specified in the configuration file are scraped.",
    )
    args = parser.parse_args()
    return args


def setup_scraping_timeframe(cfg):
    """
    Sets up the scraping timeframe for the scraping run.

    By default, this script attempts to scrape from midnight of the day prior to
    the script being executed, to 1 second before the following midnight.
    I.e. if the script is run at 2020-01-08 15:36:00, then the default scraping
    window is between 2020-01-07 00:00:00 and 2020-01-07 23:59:59.

    If the Main.start_time and Main.end_time configuration parameters in the
    ini file are supplied then this default behaviour is overruled.

    Args:
        - cfg (configparser.Namespace): Contains the script configuration
            settings.

    Returns:
        A tuple containg the (start, end) limits of the scraping window, stored
        as datetime objects.
    """
    docs_url = "https://docs.python.org/3/library/datetime.html#datetime.datetime.fromisoformat"
    error_msg = (
        "Unknown ISO 8601 format '{input}'. Available formats are described at {url}"
    )

    yesterday = date.today() - timedelta(days=1)
    try:
        start_time = datetime.fromisoformat(cfg.get("Main", "start_time"))
    except configparser.NoOptionError:
        start_time = datetime.combine(yesterday, time.min)
    except ValueError:
        raise utils.TimeError(
            "'{}' cannot be parsed as an ISO format.".format(
                cfg.get("Main", "start_time")
            )
        ) from None

    try:
        end_time = datetime.fromisoformat(cfg.get("Main", "end_time"))
    except configparser.NoOptionError:
        end_time = datetime.combine(yesterday, time.max)
    except ValueError:
        raise utils.TimeError(
            "'{}' cannot be parsed as an ISO format.".format(
                cfg.get("Main", "end_time")
            )
        ) from None

    if start_time >= end_time:
        raise utils.TimeError(
            "Start date must be earlier than end date. ({} - {})".format(
                start_time, end_time
            )
        )

    return (start_time, end_time)


def scrape(manufacturer, start, end):
    """
    Scrapes data for all devices belonging to a manufacturer.

    Args:
        - manufacturer (Manufacturer): Instance of a sub-class of Manufacturer.
        - start (datetime): The start of the scraping window.
        - end (datetime): The end of the scraping window.

    Returns:
        None, updates the raw_data attribute of a Device if the download is
        successful.
    """
    for device in manufacturer.devices:
        try:
            device.raw_data = manufacturer.scrape_device(device.web_id, start, end)
            logging.info("Download successful for device {}.".format(device.device_id))
        except utils.DataDownloadError:
            logging.error(
                "Unable to download data for device {}.".format(device.device_id)
            )
            logging.error(traceback.format_exc())
            device.raw_data = None


def process(manufacturer):
    """
    For each device belonging to a manufacturer, the raw JSON data is parsed
    into CSV format, before running a data cleaning proecedure to store only
    valid floating point values.

    Updates the Device.clean_data attribute if the CSV parse and
    subsequent QA validation procedures are successful.

    Args:
        - manufacturer (Manufacturer): Instance of a sub-class of Manufacturer.

    Returns:
        A dictionary summarising how many recordings are available for each
        device. Has the keys:
          - 'manufacturer': Provides manufacturer name as a string
          - 'devices': A further dict mapping
              {device_id: num_available_timepoints},
              where num_available_timepoints is a secondary dictionary mapping
              {measurand: # clean samples}.
              If a device has no available recordings then this value is None.
    """
    summary = {"manufacturer": manufacturer.name, "devices": {}}
    for device in manufacturer.devices:
        # Default number of clean values is 0, useful for instances where
        # there is an error in validating the data.
        # Duplicated 2 lines of code with manufacturer.validate_data(), but
        # can't a better way of handling it.
        # If obtained this from manufacturer.validate_data() then it would
        # mean that:
        # a) Have to call manufacturer.validate_data() for every device,
        #    even those that didn't have any raw data downloaded or CSV
        #    parsed failed.
        # b) validate_data() wouldn't be able to raise errors as would
        # instead return this default empty count dict.
        # This would mean either lose out on informative error messages,
        # or having to log errors from with manufacturer.validate_data(),
        # and I would rather keep logging outside of library code
        devid = device.device_id

        summary["devices"][devid] = {m["id"]: 0 for m in manufacturer.measurands}
        summary["devices"][devid]["timestamp"] = 0

        if device.raw_data is None:
            continue

        try:
            csv_data = manufacturer.parse_to_csv(device.raw_data)
            if len(csv_data) > 1:
                logging.info("Parse into CSV successful for device {}.".format(devid))
            else:
                logging.error(
                    "No time-points have been found in the parsed CSV for device {}.".format(
                        devid
                    )
                )
                continue

        except utils.DataParseError as ex:
            logging.error(
                "Unable to parse data into CSV for device {}: {}".format(devid, ex)
            )
            continue

        try:
            clean_data, measurand_summary = manufacturer.validate_data(csv_data)

            if len(clean_data) <= 1:
                logging.error(
                    "No clean measurements were found in the parsed CSV for {}.".format(
                        devid
                    )
                )
                continue

            # Success, at least 1 clean measurement has been found
            device.clean_data = clean_data
            summary["devices"][devid] = measurand_summary

        except utils.ValidateDataError as ex:
            logging.error("Data validation error for device {}: {}".format(devid, ex))

    return summary


def save_data(manufacturer, folder, day, data_type):
    """
    Iterates through all a manufacturer's devices and saves their raw or clean data to disk.

    Uses the following template filename:

    <manufacturer_name>_<deviceid>_<start_timeframe>_<end_timeframe>.<json/csv>

    Args:
        - manufacturer (Manufacturer): Instance of Manufacturer.
        - folder (str): Directory where files should be saved to.
        - day (str): Today's date, in YYYY-MM-DD format.
        - data_type (str): Either 'raw' or 'clean' to indicate which data is being
            saved.

    Returns:
        List of filenames that were successfully saved.
    """
    fns = []

    if data_type == "clean":
        fn_template = utils.CLEAN_DATA_FN
        get_data = lambda x: x.clean_data
        saving_function = utils.save_csv_file
    elif data_type == "raw":
        fn_template = utils.RAW_DATA_FN
        get_data = lambda x: x.raw_data
        saving_function = utils.save_json_file
    else:
        raise utils.DataSavingError("Unknown data type '{}'.".format(data_type))

    if not os.path.isdir(folder):
        raise utils.DataSavingError(
            "Folder {} doesn't exist, cannot save raw data.".format(folder)
        )

    for device in manufacturer.devices:
        out_fn = fn_template.substitute(
            man=manufacturer.name, device=device.device_id, day=day
        )

        data = get_data(device)
        if data is None:
            continue

        full_path = os.path.join(folder, out_fn)
        logging.info("Writing file: {}".format(full_path))
        try:
            saving_function(data, full_path)
            fns.append(full_path)
        except utils.DataSavingError as ex:
            logging.error("Unable to save file: {}".format(ex))

    return fns


def upload_data_googledrive(service, fns, folder_id, mime_type):
    """
    Uploads a number of files of the same type to a single GoogleDrive folder.

    Args:
        service (googleapiclient.discovery.Resource): Handle to GoogleAPI.
        fns (list): A list of full filepaths to the files to be uploaded.
        folder_id (str): The GoogleDrive ID of the target folder.
        mime_type (str): The MIME type of the files.

    Returns:
        None, uploads files as a side-effect.
    """
    if fns is None:
        logging.error(
            "No filenames found. Cannot upload files to Google Drive without saving them locally first. Ensure that option Main.save_<raw/clean>_data is 'true'."
        )
        return

    for fn in fns:
        try:
            logging.info("Uploading file {} to folder {}...".format(fn, folder_id))
            utils.upload_file_google_drive(service, fn, folder_id, mime_type)
            logging.info("Upload successful.")
        except utils.DataUploadError:
            logging.error("Error in upload")
            logging.error(traceback.format_exc())
            continue


def tabular_summary(summaries):
    """
    Generates a tabular summary of the run showing the number and % of available
    valid recordings for each measurand.

    Args:
        summaries (list): A list of dictionaries, with each entry storing
            information about a different manufacturer.
            Each dictionary summarises how many recordings are available for each
            device. Has the keys:
              - 'manufacturer': Provides manufacturer name as a string
              - 'devices': A further dict mapping {device_id : num_available_timepoints}
                If a device has no available recordings then the value is None.

    Returns:
        A dict, where each entry corresponds to a 2D list indexed by
        manufacturer name. The 2D list represents tabular data for the
        corresponding manufacturer, where the outer-most dimension is a row
        and the inner-most is a column.
    """
    tables = {}
    for manu in summaries:
        avail_devices = [(d, v) for d, v in manu["devices"].items() if v is not None]

        if len(avail_devices) > 0:
            manu_rows = []
            # Obtain number of expected recordings
            try:
                exp_recordings = manu["frequency"] * 24
            except KeyError:
                exp_recordings = None

            # Get header row for table, with timestamp, location first then alphabetically
            measurands = list(set([k for dev in avail_devices for k in dev[1].keys()]))
            try:
                measurands.remove("timestamp")
            except ValueError:
                pass
            try:
                measurands.remove("Location")
            except ValueError:
                pass
            measurands.sort()
            measurands.insert(0, "Location")
            measurands.insert(1, "timestamp")

            # Device ID isn't stored in measurands
            col_names = ["Device ID"] + [
                "Timestamps" if col == "timestamp" else col for col in measurands
            ]

            # Print one device on each row
            for device in avail_devices:
                # Form a list with device ID + measurements in same order as
                # column header
                row = [device[0]]
                try:
                    num_timestamps = device[1]["timestamp"]
                except KeyError:
                    num_timestamps = None

                for m in measurands:
                    try:
                        n_clean = device[1][m]
                    except KeyError:
                        n_clean = ""

                    # Value is number of clean entries, except for Location
                    # entry which is a string ('York')
                    if m == "Location":
                        col = str(n_clean)
                    else:
                        try:
                            pct = n_clean / exp_recordings * 100
                        except ZeroDivisionError:
                            pct = 0
                        except TypeError:
                            pct = None

                        if pct is not None:
                            col = "{} ({:.0f}%)".format(n_clean, pct)
                        else:
                            col = str(n_clean)

                    row.append(col)

                manu_rows.append(row)

            # Save manufacturer table
            manu_table = [col_names]
            manu_table.extend(manu_rows)
            tables[manu["manufacturer"]] = manu_table

    return tables


def generate_ascii_summary(tables, column_width=13, max_screen_width=100):
    """
    Generates an plain-text ASCII summary of the data availability table.

    If there is too much data to fit onto the screen at once (using 
    max_screen_width argument), then the table is split into sub-tables,
    each fitting within the desired screen width.

    Args:
        - tables (dict): Each entry corresponds to a 2D list indexed by
            manufacturer name. The 2D list represents tabular data for the
            corresponding manufacturer, where the outer-most dimension is a row
            and the inner-most is a column.
        - column_width (int): Column width in spaces.
        - max_screen_width (int): Maximum horizontal space to use in spaces.

    Returns:
        A list of strings, where each entry is a new line.
    """
    # Currently the code calling this function doesn't set column_width or
    # max_screen_width so they use the defaults. These values could be set from
    # the config file instead, although I don't think this will be that useful
    # so haven't implemented it
    max_cols = math.floor(max_screen_width / column_width)

    output = []
    output.append("+" * 80)
    output.append("Summary")
    output.append("-" * 80)

    for manufacturer, manu_table in tables.items():
        output.append(manufacturer)
        output.append("~" * len(manufacturer))

        # +/- 1 dotted everywhere are related to Device ID, as need to display
        # this column on every subtable, as well as usual counting <-> 0-index
        # transforms
        num_measurands = len(manu_table[0]) - 1
        cur_min_col = 1
        while num_measurands > 0:
            num_measurands_subtable = min(max_cols - 1, num_measurands)
            cur_max_col = cur_min_col + num_measurands_subtable - 1
            row_format = "||{:>{}}||" + "{:>{}}|" * num_measurands_subtable

            # Headers
            col_names = [manu_table[0][0]] + manu_table[0][
                cur_min_col : (cur_max_col + 1)
            ]
            header_vals = zip(col_names, [column_width] * (num_measurands_subtable + 1))
            header_vals = [item for sublist in header_vals for item in sublist]
            header_row = row_format.format(*header_vals)
            output.append("-" * len(header_row))
            output.append(header_row)
            output.append("-" * len(header_row))

            # Rows
            for raw_row in manu_table[1:]:
                row = [raw_row[0]] + raw_row[cur_min_col : (cur_max_col + 1)]
                row_vals = zip(row, [column_width] * (num_measurands_subtable + 1))
                row_vals = [item for sublist in row_vals for item in sublist]
                output.append(row_format.format(*row_vals))

            # Update counters for next sub-table
            num_measurands -= num_measurands_subtable
            cur_min_col = cur_max_col + 1

            # Table end horizontal line
            output.append("-" * len(header_row))

    # Summary end horizontal line
    output.append("+" * 80)

    return output


def generate_manufacturer_html(template, manufacturer, table, **kwargs):
    """
    Builds HTML summarising a manufacturer's device status.

    Args:
        template (str): The HTML template of the manufacturer section.
          Formatted as Python string.Template(), with $placeholder tags.
          Expects 3 placeholders:
              - manufacturer: Manufacturer name
              - header: Table header inside <tr> tags, so needs list of <th>.
              - body: Table body inside <tbody> tags, so needs <tr> and <td>
                tags.
        manufacturer (str): Manufacturer name.
        table (list): Python 2D list containing table contents. First entry is
            the headers, and all subsequent entries are rows.
        kwargs:
            CSS styling parameters.
            'th_style': Default style to apply to th tags.
            'td_style': Default style to apply to td tags.
            'pass_colour': Background colour for cells with 100% availability.
            'fail_colour': Background colour for cells with 0% availability.
            'warning_colour': Background colour for cells with <100% but >0% availability.

    Returns:
        A string containing HTML representing this manufacturer section.
    """
    header = table[0]
    body = table[1:]

    # Extract each cell and replace with <th> tags
    head_tags = "\n".join(
        ["<th style='{}'>{}</th>".format(kwargs["th_style"], val) for val in header]
    )
    row_tags = []
    for row in body:
        column_tags = []
        for cell in row:
            cell_style = kwargs["td_style"]

            # Add background colour formatting if cell contains a % availability
            pct_search = re.search("\(([0-9]+)\%\)", cell)
            if pct_search:
                raw_pct = pct_search.group(1)

                # Floats can be parsed as ints in Python
                # Saves having to write is_int() function
                if utils.is_float(raw_pct):
                    pct = int(raw_pct)
                else:
                    pct = -1

                if pct == 100:
                    cell_colour = kwargs["pass_colour"]
                elif pct == 0:
                    cell_colour = kwargs["fail_colour"]
                elif pct > 0 and pct < 100:
                    cell_colour = kwargs["warning_colour"]
                else:
                    cell_colour = "#ffffff"

                cell_style = cell_style + "background-color: {};".format(cell_colour)

            column_tags.append("<td style='{}'>{}</td>".format(cell_style, cell))

        row_tags.append("<tr>{}</tr>".format("\n".join(column_tags)))
    body_tags = "\n".join(row_tags)
    try:
        output = template.substitute(
            manufacturer=manufacturer, header=head_tags, body=body_tags
        )
    except ValueError:
        logging.error("Cannot fill manufacturer template placeholders.")
        output = template.template
    return output


def generate_html_summary(
    tables, email_template, manufacturer_template, manufacturer_styles
):
    """
    Generates an HTML document summarising the device availability from the
    scraping run.

    Fills in a relatively empty HTML document template with a section
    corresponding to each manufacturer included in the scraping run.

    Calls generate_manufacturer_summary() for each manufacturer and stitches
    these HTML snippets into the main document template.

    Args:
        - tables (dict): Each entry corresponds to a 2D list indexed by
            manufacturer name. The 2D list represents tabular data for the
            corresponding manufacturer, where the outer-most dimension is a row
            and the inner-most is a column.
        - email_template (str): The HTML template of the whole document.
          Formatted as Python string.Template(), with $placeholder tags.
          Expect 1 placeholder:
              - summary: Whatever HTML markup is going to consitute the body of
              this document. This placeholder is located inside a <div>, which
              is directly inside the <body> tags.
        - manufacturer_template (str): The HTML template of the manufacturer section.
        - manufacturer styles (dict): Various CSS settings to pass to
            generate_manufacturer_summary().

    Returns:
        A string containing a fully completed HTML document.
    """
    # Build HTML for each manufacturer section
    manufacturer_sections = [
        generate_manufacturer_html(
            manufacturer_template, manu, tab, **manufacturer_styles
        )
        for manu, tab in tables.items()
    ]
    manufacturer_html = "\n".join(manufacturer_sections)

    # Fill in email template
    try:
        email_html = email_template.substitute(summary=manufacturer_html)
    except ValueError:
        logging.error("Cannot fill email template placeholders.")
        email_html = email_template.template

    return email_html


def main():
    """
    Entry point into the script.

    Args:
        - None

    Returns: None.
    """
    # This sets up environment variables if they are explicitly provided in a .env
    # file. If system env variables are present (as they will be in production),
    # then it doesn't overwrite them
    load_dotenv()

    # Setup logging, which for now just logs to stderr
    try:
        setup_loggers()
    except utils.SetupError:
        logging.error("Error in setting up loggers.")
        logging.error(traceback.format_exc())
        logging.error("Terminating program")
        sys.exit()

    # Parse args and config file
    args = parse_args()

    try:
        cfg = utils.setup_config(CONFIG_FN)
    except utils.SetupError:
        logging.error("Error in setting up configuration properties")
        logging.error(traceback.format_exc())
        logging.error("Terminating program")
        sys.exit()

    # TODO Refactor into own function in utils
    with open(DEVICES_FN, "r") as infile:
        device_config = json.load(infile)

    start_time, end_time = setup_scraping_timeframe(cfg)

    manufacturers, _ = setup_manufacturers(device_config["manufacturers"], args.devices)

    # Store device availability summary for each manufacturer
    summaries = []

    for manufacturer in manufacturers:
        logging.info("Manufacturer: {}".format(manufacturer.name))

        try:
            logging.info("Attempting to connect...")
            manufacturer.connect()
            logging.info("Connection established")
        except utils.LoginError:
            logging.error(
                "Cannot establish connection to {}.".format(manufacturer.name)
            )
            logging.error(traceback.format_exc())
            continue

        logging.info("Downloading data from all devices:")
        scrape(manufacturer, start_time, end_time)
        logging.info("Processing raw data for all devices:")
        man_summary = process(manufacturer)

        # Add device location and recording rate so can be displayed in summary
        # table
        for device in manufacturer.devices:
            if man_summary["devices"][device.device_id] is not None:
                man_summary["devices"][device.device_id]["Location"] = device.location
        man_summary["frequency"] = manufacturer.recording_frequency
        summaries.append(man_summary)

        # Get start time date for naming output files
        start_fmt = start_time.strftime("%Y-%m-%d")

        if cfg.getboolean("Main", "save_raw_data"):
            logging.info("Saving raw data from all devices:")
            raw_fns = save_data(
                manufacturer,
                cfg.get("Main", "local_folder_raw_data"),
                start_fmt,
                "raw",
            )

        if cfg.getboolean("Main", "save_clean_data"):
            logging.info("Saving cleaned CSV data from all devices:")
            clean_fns = save_data(
                manufacturer,
                cfg.get("Main", "local_folder_clean_data"),
                start_fmt,
                "clean",
            )

        upload_raw = cfg.getboolean("Main", "upload_raw_googledrive")
        upload_clean = cfg.getboolean("Main", "upload_clean_googledrive")

        if upload_raw or upload_clean:
            try:
                service = utils.auth_google_api(cfg.get("GoogleAPI", "credentials_fn"))
            except utils.GoogleAPIError:
                logging.error("Cannot connect to Google API.")
                logging.error(traceback.format_exc())
                break

            if upload_raw:
                logging.info("Uploading raw data to Google Drive:")
                upload_data_googledrive(
                    service, raw_fns, cfg.get("GoogleAPI", "raw_data_id"), "text/json"
                )

            if upload_clean:
                logging.info("Uploading clean CSV data to Google Drive:")
                upload_data_googledrive(
                    service,
                    clean_fns,
                    cfg.get("GoogleAPI", "clean_data_id"),
                    "text/csv",
                )

    # Summarise number of clean measurands into tabular format
    summary_tables = tabular_summary(summaries)

    # Output table to screen
    ascii_summary = generate_ascii_summary(summary_tables)
    # Print summary to log and stdout
    for line in ascii_summary:
        logging.info(line)
    for line in ascii_summary:
        print(line)

    # Add HTML summary if requested
    if cfg.getboolean("Main", "save_html_summary"):

        # Load both templates
        email_template_fn = cfg.get("HTMLSummary", "email_template")
        manufacturer_template_fn = cfg.get("HTMLSummary", "manufacturer_template")

        try:
            email_template = utils.load_html_template(email_template_fn)
        except utils.DataReadingError as ex:
            logging.error("Cannot load email HTML template: {}".format(ex))
            email_template = None
        try:
            manufacturer_template = utils.load_html_template(manufacturer_template_fn)
        except utils.DataReadingError as ex:
            logging.error("Cannot load manufacturer HTML template: {}".format(ex))
            manufacturer_template = None

        # Load style options for manufacturer summary
        styles = {
            "th_style": cfg.get("HTMLSummary", "th_style"),
            "td_style": cfg.get("HTMLSummary", "td_style"),
            "pass_colour": cfg.get("HTMLSummary", "pass_colour"),
            "fail_colour": cfg.get("HTMLSummary", "fail_colour"),
            "warning_colour": cfg.get("HTMLSummary", "warning_colour"),
        }

        if email_template is not None and manufacturer_template is not None:
            email_html = generate_html_summary(
                summary_tables, email_template, manufacturer_template, styles,
            )

        try:
            utils.save_plaintext(email_html, cfg.get("HTMLSummary", "filename"))
        except utils.DataSavingError as ex:
            logging.error("Unable to save HTML email: {}".format(ex))


if __name__ == "__main__":
    main()
