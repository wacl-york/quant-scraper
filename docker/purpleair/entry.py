#!/env/python3
"""
    Entry point for the container.

    Runs the PurpleAir conversion script to clean and validate all PurpleAir
    files that aren't in the main QUANT Clean repository.
    Then preprocesses these newly validated files to produce the Analysis files
    that are subsequently uploaded to Google Drive.
"""

import argparse
import subprocess


def main():
    args = parse_args()

    # Base calls
    scrape_call = ["purpleair_convert"]
    preprocess_call = ["purpleair_preprocess"]

    # Add arguments if passed in
    if args.recipients is not None:
        scrape_call.extend(["--recipients", *args.recipients])

    print("Calling purpleair_convert with call: {}".format(scrape_call))
    subprocess.run(scrape_call)
    print("Calling purpleair_preprocess with call: {}".format(preprocess_call))
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
