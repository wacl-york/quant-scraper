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


def main():
    email_fn = "email.html"
    args = parse_args()

    # Base calls
    scrape_call = ["quant_scrape", "--save-raw", "--save-clean", "--html", email_fn]
    preprocess_call = ["quant_preprocess"]

    # Add arguments if passed in
    if args.date is not None:
        scrape_call.extend(["--start", args.date, "--end", args.date])
        preprocess_call.extend(["--date", args.date])

    if args.scrape_devices is not None:
        scrape_call.append("--devices")
        for dev in args.scrape_devices:
            scrape_call.append(dev)

    if args.upload_raw:
        scrape_call.append("--upload-raw")

    if args.upload_clean:
        scrape_call.append("--upload-clean")

    if args.preprocess_devices is not None:
        preprocess_call.append("--devices")
        for dev in args.preprocess_devices:
            preprocess_call.append(dev)

    if args.upload_preprocess:
        preprocess_call.append("--upload")

    subprocess.run(scrape_call)
    subprocess.run(preprocess_call)

    # TODO Add emailing HTML table here


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
        "--upload-preprocess",
        action="store_true",
        help="Uploads pre-processed data to Google Drive.",
    )

    args = parser.parse_args()
    return args


if __name__ == "__main__":
    main()
