#!/env/python3
"""
    run_scrape.py
    ~~~~~~~~~~~~~

    Runs the QUANTscraping program on AWS through Fargate.

    Depends upon having a file called "run.env" in the path, containing
    AWS runtime properties:
        CLUSTER_ID=<name of cluster>
        AWS_TASK_PROFILE=<name of AWS profile in ~/.aws/credentials that has IAM
            access to run the task>
        QUANT_TASK_ARN=<arn of task to run>
        SUBNET_1=<subnet id>
        SUBNET_2=<subnet id>
        SECURITY_GROUP=<security group id>
        AWS_CLI_REGION=<region to run the task in>

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
    # There's almost certainly a neater way of passing arguments through but
    # I'll keep this for now
    cmd = []

    if args.date is not None:
        cmd.extend(["--date", args.date])

    if args.scrape_devices is not None:
        cmd.extend(["--scrape-devices", *args.scrape_devices])

    if args.preprocess_devices is not None:
        cmd.extend(["--preprocess-devices", *args.preprocess_devices])

    if args.recipients is not None:
        cmd.extend(["--recipients", *args.recipients])

    if args.gdrive_raw_id is not None:
        cmd.extend(["--gdrive-raw-id", args.gdrive_raw_id])

    if args.gdrive_clean_id is not None:
        cmd.extend(["--gdrive-clean-id", args.gdrive_clean_id])

    if args.gdrive_availability_id is not None:
        cmd.extend(["--gdrive-availability-id", args.gdrive_availability_id])

    if args.gdrive_analysis_id is not None:
        cmd.extend(["--gdrive-analysis-id", args.gdrive_analysis_id])

    if args.subject is not None:
        cmd.extend(["--subject", args.subject])

    overrides = {}
    if len(cmd) > 0:
        overrides = {"containerOverrides": [{"name": "quant", "command": cmd}]}

    session = boto3.Session(
        profile_name=os.environ["AWS_TASK_PROFILE"],
        region_name=os.environ["AWS_CLI_REGION"],
    )
    client = session.client("ecs")
    run_task_response = client.run_task(
        cluster=os.environ["CLUSTER_ID"],
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
