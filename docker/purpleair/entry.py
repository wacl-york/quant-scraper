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

    if args.gdrive_clean_id is not None:
        scrape_call.extend(["--gdrive-clean-id", args.gdrive_clean_id])

    if args.gdrive_availability_id is not None:
        scrape_call.extend(["--gdrive-availability-id", args.gdrive_availability_id])

    if args.gdrive_pa_id is not None:
        scrape_call.extend(["--gdrive-pa-id", args.gdrive_pa_id])

    if args.gdrive_quant_shared_id is not None:
        scrape_call.extend(["--gdrive-quant-shared-id", args.gdrive_quant_shared_id])
        preprocess_call.extend(
            ["--gdrive-quant-shared-id", args.gdrive_quant_shared_id]
        )

    if args.gdrive_analysis_id is not None:
        preprocess_call.extend(["--gdrive-analysis-id", args.gdrive_analysis_id])

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
    parser = argparse.ArgumentParser(description="PurpleAir data conversion script.")

    parser.add_argument(
        "--recipients",
        metavar="EMAIL@DOMAIN",
        nargs="+",
        help="The recipients to send the email to. If not provided, then no email is sent.",
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
        "--gdrive-pa-id",
        help="Google Drive staging folder where PurpleAir files are manually uploaded to.",
        required=True,
    )

    parser.add_argument(
        "--gdrive-quant-shared-id", help="Id of QUANT Shared Drive.", required=True
    )

    parser.add_argument(
        "--gdrive-analysis-id",
        help="Google Drive analysis data folder to upload to. If not provided then files aren't uploaded.",
    )

    args = parser.parse_args()
    return args


if __name__ == "__main__":
    main()
