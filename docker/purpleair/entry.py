#!/env/python3
"""
    Entry point for the container.

    Runs the PurpleAir conversion script to clean and validate all PurpleAir
    files that aren't in the main QUANT Clean repository.
"""

import argparse
import subprocess
from datetime import date, timedelta


def main():
    args = parse_args()

    # Base calls
    scrape_call = ["quant_convert_purpleair"]
    # TODO How to handle preprocessing?!
    # As the date loop is inside the quant_convert_purpleair.py script
    preprocess_call = ["quant_preprocess --upload"]

    # Add arguments if passed in
    if args.recipients is not None:
        scrape_call.extend(["--recipients", *args.recipients])

    print("Calling quant_scrape with call: {}".format(scrape_call))
    subprocess.run(scrape_call)
    print("Calling quant_preprocess with call: {}".format(preprocess_call))
    subprocess.run(preprocess_call)


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
        "--recipients",
        metavar="EMAIL@DOMAIN",
        nargs="+",
        help="The recipients to send the email to. If not provided, then no email is sent.",
    )

    args = parser.parse_args()
    return args


if __name__ == "__main__":
    main()
