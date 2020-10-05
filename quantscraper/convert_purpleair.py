"""
    convert_purpleair.py
    ~~~~~~~~~~~~~~~~~~~~

    Downloads newly obtained data from Purple Air devices and uploads it to the
    main QUANT/Data/Clean folder after validating it.

    Purple Air devices produce a separate file per day of recording and saves
    them onto a local SD card.
    This SD card is obtained from a project member and all the files are
    manually uploaded to a specific Google Drive folder (hereafterto referred to
    as the 'source').

    This script looks for recording days in the source folder that aren't
    present in the main QUANT Clean folder.
    It downloads these missing files from source, runs them through the usual
    validation routines and formats them into the same 3 column long format and
    uploads them into Clean.

    A summary email can be sent summarising the data availability.
"""

import sys
import os
import traceback
import argparse
import logging
from datetime import datetime
import quantscraper.utils as utils
import quantscraper.cli as cli
from quantscraper.factories import setup_manufacturers


def main():
    """
    The main function and the only entry point into the script.

    Args:
        None
    
    Returns:
        None
    """
    # Setup logging
    try:
        utils.setup_loggers()
    except utils.SetupError:
        print("Error in setting up loggers.")
        print(traceback.format_exc())
        sys.exit()

    # Read inputs from CLI and env vars
    args = parse_args()
    # This sets up environment variables if they are explicitly provided in a .env
    # file. If system env variables are present (as they will be in production),
    # then it doesn't overwrite them
    if not utils.parse_env_vars("QUANT_CREDS", "EMAIL_CREDS"):
        logging.error(
            "Error when initiating environment variables, terminating execution."
        )
        logging.error(traceback.format_exc())
        sys.exit()

    try:
        clean_drive_id = os.environ["GDRIVE_CLEAN_ID"]
        toplevel_drive_id = os.environ["GDRIVE_QUANTSHARED_ID"]
        pa_drive_id = os.environ["GDRIVE_PURPLEAIR_ID"]
        availability_id = os.environ["GDRIVE_AVAILABILITY_ID"]

    except KeyError:
        logging.error(
            "Ensure the env vars 'GDRIVE_CLEAN_ID', 'GDRIVE_AVAILABILITY_ID', 'GDRIVE_QUANTSHARED_ID', and 'GDRIVE_PURPLEAIR_ID' are set prior to running this program."
        )
        sys.exit()

    try:
        cfg = utils.setup_config()
    except utils.SetupError:
        logging.error("Error in setting up configuration properties")
        logging.error(traceback.format_exc())
        sys.exit()

    # Connect to Google Drive API
    try:
        # Permission to access files outside of those created by this service
        service = utils.auth_google_api(
            scopes=["https://www.googleapis.com/auth/drive"]
        )
    except utils.GoogleAPIError:
        logging.error("Cannot connect to Google API.")
        logging.error(traceback.format_exc())
        sys.exit()

    PA_manufacturer = instantiate_PA_manufacturer()
    if PA_manufacturer is None:
        logging.error("Could not instantiate PurpleAir")
        logging.error(traceback.format_exc())
        sys.exit()

    summaries = {}

    for device in PA_manufacturer.devices:

        logging.info(
            f"Device {device.device_id}: searching for recordings that haven't been uploaded to the main QUANT repository."
        )

        # Get list of filenames in Google Drive
        raw_fns = get_raw_filenames(
            service, toplevel_drive_id, pa_drive_id, device.device_id
        )

        # Get list of filenames in Clean folder
        clean_fns = get_processed_filenames(
            service, toplevel_drive_id, clean_drive_id, device.device_id
        )

        # Obtain list of files to download
        files_to_download = []
        for x in raw_fns:
            clean_fn = convert_to_clean_fn(
                x[0], device.device_id, cfg.get("Main", "filename_date_format")
            )
            if clean_fn not in clean_fns:
                if clean_fn is None:
                    logging.error(f"Unable to parse date from {x[0]}")
                    continue
                files_to_download.append(x)

        # Remove Nones (indicating unparseable date)
        files_to_download = [fn for fn in files_to_download if fn is not None]

        logging.info(
            f"Found {len(files_to_download)} recordings that aren't in the Clean repository"
        )

        # Download these files
        for file in files_to_download:
            logging.info(f"Processing file {file[0]}...")
            fh = utils.download_file(service, file[1])
            raw_data = fh.getvalue().decode("utf-8")

            # Parse to CSV and validate
            try:
                csv_data = PA_manufacturer.parse_to_csv(raw_data)
            except utils.DataParseError as ex:
                logging.error("Unable to parse {} into CSV: {}".format(file[0], ex))
                continue

            try:
                validated_data, summary = PA_manufacturer.validate_data(
                    csv_data, cfg.get("Main", "timestamp_format")
                )
            except utils.ValidateDataError as ex:
                logging.error("Data validation error for {}: {}".format(file[0], ex))

            logging.info("Successfully cleaned. Uploading to Google Drive.")

            # Save data and upload to Google Drive
            out_fn = os.path.join(
                cfg.get("Main", "local_folder_clean_data"),
                convert_to_clean_fn(
                    file[0], device.device_id, cfg.get("Main", "filename_date_format")
                ),
            )
            success = upload_data(validated_data, out_fn, clean_drive_id, service)
            if not success:
                continue

            # Store summary indexed by device ID
            date = get_date_from_purpleair_fn(
                file[0], cfg.get("Main", "filename_date_format")
            )
            if date is None:
                continue  # Shouldn't be reached. already checked can be parsed
            if date not in summaries:
                summaries[date] = {device.device_id: summary}
            else:
                summaries[date][device.device_id] = summary

    # Combine summaries into 2D list
    tables = tabular_summary(summaries, PA_manufacturer.recording_frequency)

    # Upload availability statistics
    for date, summary in tables.items():
        cli.save_availability(
            service,
            {"PurpleAir": summary},
            availability_id,
            cfg.get("Main", "local_folder_availability"),
            date,
        )

    # Email HTML availability summary if requested
    if args.recipients is not None:

        email_html = generate_html_summary(tables, cfg)

        try:
            sender = os.environ["EMAIL_SENDER_ADDRESS"]
        except KeyError:
            logging.error(
                "Error: no EMAIL_SENDER_ADDRESS environment variable. Set this to the email address that is sending the email."
            )
        try:
            identity_arn = os.environ["IDENTITY_ARN"]
        except KeyError:
            logging.error(
                "Error: no IDENTITY_ARN environment variable. Set this to ARN of the identity that is authorised to send emails from the EMAIL_SENDER_ADDRESS"
            )

        try:
            logging.info("Attemping to send email...")
            utils.send_email_ses(
                "PurpleAir upload summary",
                email_html,
                f"Unable to render HTML. Please open the following content in a web browser\r\n{email_html}",
                sender,
                args.recipients,
                identity_arn,
            )
        except utils.EmailSendingError as ex:
            logging.error("Email sending failed: {}".format(ex))
        else:
            logging.info("Email sent.")


def instantiate_PA_manufacturer():
    """
    Instantiates the PurpleAir Manufacturer sub-class.

    This function loads the JSON file containing the details of all the air
    quality instruments in the project, subsets it to PurpleAir, and uses the
    factory method to load the instance.

    Args:
        - None.

    Returns:
        An instance of PurpleAir.
    """
    try:
        device_config = utils.load_device_configuration()
    except utils.SetupError as ex:
        logging.error("Cannot load device configuration: {}.".format(ex))
        return None

    # Instantiate PA Manufacturer
    pa_config = [m for m in device_config["manufacturers"] if m["name"] == "PurpleAir"]
    manufacturers = setup_manufacturers(pa_config)

    if len(manufacturers) != 1:
        logging.error("No manufacturer created.")
        return None

    PA_manufacturer = manufacturers[0]
    return PA_manufacturer


def parse_args():
    """
    Parses CLI arguments to the script.

    Args:
        - None.

    Returns:
        An argparse.Namespace object.
    """
    parser = argparse.ArgumentParser(
        description="Convert raw PurpleAir data to QUANT format"
    )
    parser.add_argument(
        "--recipients",
        metavar="EMAIL@DOMAIN",
        nargs="+",
        help="The recipients to send the email to.",
    )

    args = parser.parse_args()
    return args


def generate_html_summary(tables, cfg):
    """
    Generates an HTML document summarising the device availability from the
    scraping run.

    NB: This is almost identical to a function in quantscraper/cli.py and should
    really be refactored.

    Args:
        - tables (dict): Each entry corresponds to a 2D list indexed by
            manufacturer name. The 2D list represents tabular data for the
            corresponding manufacturer, where the outer-most dimension is a row
            and the inner-most is a column.
        - cfg (dict): Configuration object from the ini file.

    Returns:
        A string containing a fully completed HTML document.
    """
    styles = {k: cfg["HTMLSummary"][k] for k in cfg["HTMLSummary"]}

    try:
        email_template = utils.load_html_template(
            cfg.get("PurpleAirUpload", "email_template")
        )
    except utils.DataReadingError as ex:
        logging.error("Cannot load email HTML template: {}".format(ex))
        return None
    try:
        summary_template = utils.load_html_template(
            cfg.get("HTMLSummary", "summary_table_template")
        )
    except utils.DataReadingError as ex:
        logging.error("Cannot load manufacturer HTML template: {}".format(ex))
        return None

    # Build HTML for each manufacturer section
    day_sections = [
        cli.generate_manufacturer_html(summary_template, date, tab, **styles)
        for date, tab in tables.items()
    ]
    day_html = "\n".join(day_sections)

    # Fill in email template
    try:
        email_html = email_template.substitute(summary=day_html)
    except ValueError:
        logging.error("Cannot fill email template placeholders.")
        email_html = email_template.template

    return email_html


def upload_data(data, fn, folder_id, service):
    """
    Uploads CSV data to Google Drive.

    The data is firstly saved to file and then uploaded, as files can't be
    uploaded to GoogleDrive from memory.

    Args:
        - data (list): CSV data in 2D list.
        - fn (str): Filename to use when saving and uploading the file.
        - folder_id (str): Google Drive folder id of the target upload location.
        - service (googleapiclient.discovery.Resource): Handle to GoogleAPI.

    Returns:
        None, uploads data as a side-effect.
    """
    try:
        utils.save_csv_file(data, fn)
    except utils.DataSavingError as ex:
        logging.error("Unable to save file: {}".format(ex))
        return False

    # Upload to Clean Google Drive
    try:
        logging.info("Uploading file {} to folder {}...".format(fn, folder_id))
        utils.upload_file_google_drive(service, fn, folder_id, "text/csv")
        logging.info("Upload successful.")
    except utils.DataUploadError:
        logging.error("Error in upload")
        logging.error(traceback.format_exc())
        return False

    return True


def tabular_summary(summaries, hourly_rate):
    """
    Generates a tabular summary of the run showing the number and % of available
    valid recordings for each measurand.

    NB: This is very similar to tabular_summary() in cli.py and should probably be
    refactored.
    The main differences are that this function assumes the total period is 24
    hours rather than allowing for a full day, and that only 1 manufacturer is
    represented (PurpleAir).

    Args:
        - summaries (dict): Availability data indexed by date in the form
            YYYY-mm-dd. Each entry is a further dictionary indexed by 
            device id, giving the summary statistics for that device for 
            that recording date.
        - hourly_rate (int): Number of expected recordings in an hour.

    Returns:
        A dict indexed by dates, with the values being dicts mapping device IDs
        to tabular data stored as a 2D list.
    """
    tables = {}
    exp_recordings = 24 * hourly_rate
    for date in sorted(summaries, reverse=True):
        day_rows = []
        # Obtain number of expected recordings
        avail_devices = list(summaries[date].keys())

        # Get header row for table, with timestamp, location first then alphabetically
        measurands = list(
            set(k for dev in avail_devices for k in summaries[date][dev].keys())
        )
        try:
            measurands.remove("timestamp")
        except ValueError:
            pass
        measurands.sort()
        measurands.insert(0, "timestamp")

        # Device ID isn't stored in measurands
        col_names = ["Device ID"] + [
            "Timestamps" if col == "timestamp" else col for col in measurands
        ]

        # Print one device on each row
        for device in avail_devices:
            # Form a list with device ID + measurements in same order as
            # column header
            row = [device]

            dev_summary = summaries[date][device]

            for m in measurands:
                try:
                    n_clean = dev_summary[m]
                except KeyError:
                    n_clean = ""

                # Value is number of clean entries
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

            day_rows.append(row)

        # Save manufacturer table
        day_table = [col_names]
        day_table.extend(day_rows)
        tables[date] = day_table

    return tables


def get_date_from_purpleair_fn(fn, quant_date_format, pa_date_format="%Y%m%d"):
    """
    Obtains the recording date from the filename convention used by PurpleAir
    devices.

    Args:
        - fn (str): The filename as automatically generated by PurpleAir
            software.
        - quant_date_format (str): The date formatting convention used in
            filenames by QUANT.
        - pa_date_format (optional, str): The date formatting convention used by
            PurpleAir. Set as an argument in case it gets changed later on.

    Returns:
        The date in YYYY-mm-dd format as a string.
    """
    # Remove file extension and path in case present
    fn = os.path.basename(fn)
    fn = os.path.splitext(fn)[0]

    # Parse into datetime and format in ISO
    try:
        date = datetime.strptime(fn, pa_date_format).strftime(quant_date_format)
    except ValueError:
        return None
    else:
        return date


def convert_to_clean_fn(raw_fn, device_id, quant_date_format):
    """
    Converts the filename automatically generated by PurpleAir devices into the
    QUANT naming convention.

    Args:
        - raw_fn (str): The original PurpleAir filename.
        - device_id (str): Device ID that recorded this filename. This
            information needs to be explicitly passed in as it isn't present in the
            original filename.
        - quant_date_format (str): The date formatting convention used in
            filenames by QUANT.

    Returns:
        A string containing the new filename.
    """
    date = get_date_from_purpleair_fn(raw_fn, quant_date_format)
    if not date:
        return None
    else:
        fn = utils.CLEAN_DATA_FN.substitute(man="PurpleAir", device=device_id, day=date)
        return fn


def get_processed_filenames(service, drive_id, clean_id, device_id):
    """
    Finds PurpleAir files that have already been uploaded to the QUANT
    repository for a given device.

    Args:
        - service (googleapiclient.discovery.Resource): Handle to GoogleAPI.
        - drive_id (str): The ID of the top-level QUANT shared drive.
        - clean_id (str): The ID of the QUANT/Data/Clean repository.
        - device_id (str): Device ID.

    Returns:
        A list of filenames in the standard QUANT naming convention.
    """
    q = f"mimeType='text/csv' and '{clean_id}' in parents and name contains 'PurpleAir_{device_id}_'"
    files = utils.list_files_googledrive(service, drive_id, query=q)
    return [f["name"] for f in files]


def get_raw_filenames(service, drive_id, pa_id, device_id):
    """
    Finds all filenames in the raw PurpleAir source folder for a given device.

    Args:
        - service (googleapiclient.discovery.Resource): Handle to GoogleAPI.
        - drive_id (str): The ID of the top-level QUANT shared drive.
        - pa_id (str): The ID of the raw PurpleAir Google Drive folder.
        - device_id (str): Device ID.

    Returns:
        A list of filenames.
    """
    # Find device folder as sub folder of PurpleAir folder
    q = f"mimeType='application/vnd.google-apps.folder' and '{pa_id}' in parents and name='{device_id}'"
    folder = utils.list_files_googledrive(service, drive_id, query=q)
    folder_id = folder[0]["id"]

    # Find all location subfolders belonging to this device
    q = f"mimeType='application/vnd.google-apps.folder' and '{folder_id}' in parents"
    location_folders = utils.list_files_googledrive(service, drive_id, query=q)
    location_folder_ids = [f["id"] for f in location_folders]

    fns = []
    # Pull the filenames from all location subfolders
    for location_id in location_folder_ids:
        q = f"mimeType='text/csv' and '{location_id}' in parents"
        csv_files = utils.list_files_googledrive(service, drive_id, query=q)
        fns.extend([(fn["name"], fn["id"]) for fn in csv_files])
    return fns


if __name__ == "__main__":
    main()
