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
    email_fn = "email.html"
    args = parse_args()

    # Default date to yesterday
    if args.date is None:
        parse_date = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        parse_date = args.date

    # Base calls
    scrape_call = ["quant_scrape", "--save-raw", "--save-clean", "--html", email_fn]
    preprocess_call = ["quant_preprocess"]
    email_call = ["python", "send_email.py", "--file", email_fn]

    # Always pass in date
    scrape_call.extend(["--start", parse_date, "--end", parse_date])
    preprocess_call.extend(["--date", parse_date])
    email_call.extend(["--date", parse_date])

    # Add arguments if passed in
    if args.scrape_devices is not None:
        scrape_call.extend(["--devices", *args.scrape_devices])

    if args.upload_raw:
        scrape_call.append("--upload-raw")

    if args.upload_clean:
        scrape_call.append("--upload-clean")

    if args.upload_availability:
        scrape_call.append("--upload-availability")

    if args.preprocess_devices is not None:
        preprocess_call.extend(["--devices", *args.preprocess_devices])

    if args.upload_preprocess:
        preprocess_call.append("--upload")

    print("Calling quant_scrape with call: {}".format(scrape_call))
    subprocess.run(scrape_call)
    print("Calling quant_preprocess with call: {}".format(preprocess_call))
    subprocess.run(preprocess_call)

    # Only send email if have provided recipients
    if args.recipients is not None:
        email_call.extend(["--recipients", *args.recipients])
        print("Calling send_email with call: {}".format(email_call))
        subprocess.run(email_call)


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
        "--upload-raw", action="store_true", help="Uploads raw data to Google Drive.",
    )

    parser.add_argument(
        "--upload-clean",
        action="store_true",
        help="Uploads clean data to Google Drive.",
    )

    parser.add_argument(
        "--upload-availability",
        action="store_true",
        help="Uploads availability data to Google Drive.",
    )

    parser.add_argument(
        "--upload-preprocess",
        action="store_true",
        help="Uploads pre-processed data to Google Drive.",
    )

    parser.add_argument(
        "--recipients",
        metavar="EMAIL@DOMAIN",
        nargs="+",
        help="The recipients to send the email to. If not provided, then no email is sent.",
    )

    args = parser.parse_args()
    return args


if __name__ == "__main__":
    main()
