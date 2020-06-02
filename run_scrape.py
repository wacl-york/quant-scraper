#!/env/python3
"""
    run_scrape.py
    ~~~~~~~~~~~~~

    Runs the QUANTscraping program on AWS through Fargate.

    Depends upon having a file called "run.env" in the path, containing
    AWS runtime properties:
        QUANT_TASK_ARN=<arn of task to run>
        SUBNET_1=<subnet id>
        SUBNET_2=<subnet id>
        SECURITY_GROUP=<security group id>

    Runs the scraping and pre-processing functionalities for a single day by
    calling the appropriate commands.

    Passes user options in for the devices included in scraping and
    pre-processing, as well as allowing the user to select the scraping date.

    By default, runs a scrape of all devices listed in devices.json from the
    previous day, and pre-processes all their data.
"""

import sys
import json
import argparse
import os
import boto3
from dotenv import load_dotenv


def main():
    env_fn = "run.env"

    if not os.path.isfile(env_fn):
        print("Error: file {} not found. Terminating execution.".format(env_fn))
        sys.exit()

    # Load environment parameters containing AWS runtime details
    load_dotenv(dotenv_path=env_fn)

    args = parse_args()

    # Sets up arguments to use to call the container entry point script with
    if (
        args.date is not None
        or args.preprocess_devices is not None
        or args.scrape_devices is not None
    ):
        cmd = []

        if args.date is not None:
            cmd.extend(["--date", args.date])

        if args.scrape_devices is not None:
            cmd.extend(["--scrape-devices", *args.scrape_devices])

        if args.preprocess_devices is not None:
            cmd.extend(["--preprocess-devices", *args.preprocess_devices])

        if args.recipients is not None:
            cmd.extend(["--recipients", *args.recipients])

        if args.upload_clean:
            cmd.append("--upload-clean")

        if args.upload_raw:
            cmd.append("--upload-raw")

        if args.upload_preprocess:
            cmd.append("--upload-preprocess")

        overrides = {"containerOverrides": [{"name": "quant", "command": cmd}]}
    else:
        overrides = {}

    client = boto3.client("ecs")
    run_task_response = client.run_task(
        cluster="default",
        taskDefinition=os.environ["QUANT_TASK_ARN"],
        count=1,
        launchType="FARGATE",
        overrides=overrides,
        networkConfiguration={
            "awsvpcConfiguration": {
                "subnets": [os.environ["SUBNET_1"], os.environ["SUBNET_2"],],
                "securityGroups": [os.environ["SECURITY_GROUP"],],
                "assignPublicIp": "ENABLED",
            },
        },
    )
    print(json.dumps(run_task_response, default=str))


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
