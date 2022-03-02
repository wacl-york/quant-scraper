#!/env/python3
"""
    Entry point for the container.
    Runs the scraping and pre-processing functionalities for a single day by
    calling the appropriate commands.

    Passes user options in for the devices included in scraping and
    pre-processing, as well as allowing the user to select the scraping date.

    By default, runs a scrape of all devices listed in devices.json from the
    previous day, and pre-processes all their data.
"""

import argparse
import subprocess
from datetime import date, timedelta


def main():
    args = parse_args()

    # Default date to yesterday
    if args.date is None:
        parse_date = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        parse_date = args.date

    # Base calls
    scrape_call = ["quant_scrape", "--save-raw", "--save-clean"]

    # Always pass in date
    scrape_call.extend(["--start", parse_date, "--end", parse_date])

    # Add arguments if passed in
    if args.scrape_devices is not None:
        scrape_call.extend(["--devices", *args.scrape_devices])

    if args.gdrive_raw_id is not None:
        scrape_call.extend(["--gdrive-raw-id", args.gdrive_raw_id])

    if args.gdrive_clean_id is not None:
        scrape_call.extend(["--gdrive-clean-id", args.gdrive_clean_id])

    if args.gdrive_availability_id is not None:
        scrape_call.extend(["--gdrive-availability-id", args.gdrive_availability_id])

    if args.recipients is not None:
        scrape_call.extend(["--recipients", *args.recipients])

    if args.subject is not None:
        scrape_call.extend(["--subject", args.subject])

    print("Calling quant_scrape with call: {}".format(scrape_call))
    subprocess.run(scrape_call)


def parse_args():
    """
    Parses CLI arguments to the script.

    Args:
        - None

    Returns:
        An argparse.Namespace object.
    """
    parser = argparse.ArgumentParser(description="Daily scraping container")
    parser.add_argument(
        "--scrape-devices",
        metavar="DEVICE1 DEVICE2 ... DEVICEN",
        nargs="+",
        help="Specify the device IDs to include in the scraping. If not provided then all the devices specified in the configuration file are scraped.",
    )

    parser.add_argument(
        "--preprocess-devices",
        metavar="DEVICE1 DEVICE2 ... DEVICEN",
        nargs="+",
        help="Specify the device IDs to include in the pre-processing. If not provided then all the devices specified in the configuration file are scraped.",
    )

    parser.add_argument(
        "--date",
        metavar="DATE",
        help="The date to download data for (inclusive). Must be in the format YYYY-mm-dd. Defaults to the previous day.",
    )

    parser.add_argument(
        "--gdrive-raw-id",
        help="Google Drive raw data folder to upload to. If not provided then files aren't uploaded.",
    )

    parser.add_argument(
        "--gdrive-clean-id",
        help="Google Drive clean data folder to upload to. If not provided then files aren't uploaded.",
    )

    parser.add_argument(
        "--gdrive-availability-id",
        help="Google Drive availability data folder to upload to. If not provided then availability logs aren't uploaded.",
    )

    parser.add_argument(
        "--gdrive-analysis-id",
        help="Google Drive analysis data folder to upload to. If not provided then files aren't uploaded.",
    )

    parser.add_argument(
        "--recipients",
        metavar="EMAIL@DOMAIN",
        nargs="+",
        help="The recipients to send the email to. If not provided, then no email is sent.",
    )

    parser.add_argument(
        "--subject",
        default="QUANT scraping summary",
        help="The subject line to use with the email. The date is always appended in the form '<subject> - <date>'",
    )

    args = parser.parse_args()
    return args


if __name__ == "__main__":
    main()
