#!/env/python3
"""
    run_purpleair.py
    ~~~~~~~~~~~~~~~~

    Runs the PurpleAir conversion program on AWS through Fargate.

    Depends upon having a file called "run.env" in the path, containing
    AWS runtime properties:
        CLUSTER_ID=<name of cluster>
        AWS_TASK_PROFILE=<name of AWS profile in ~/.aws/credentials that has IAM
            access to run the task>
        PURPLEAIR_TASK_ARN=<arn of task to run>
        SUBNET_1=<subnet id>
        SUBNET_2=<subnet id>
        SECURITY_GROUP=<security group id>
        AWS_CLI_REGION=<region to run the task in>

    Downloads newly obtained data from Purple Air devices and uploads it to the
    main QUANT/Data/Clean folder after validating it.
    A summary email can be sent summarising the data availability, and the
    resulting cleaned data is converted into the wide 'Analysis' format.
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

    if args.recipients is not None:
        cmd = ["--recipients", *args.recipients]
        overrides = {"containerOverrides": [{"name": "PA", "command": cmd}]}
    else:
        overrides = {}

    session = boto3.Session(
        profile_name=os.environ["AWS_TASK_PROFILE"],
        region_name=os.environ["AWS_CLI_REGION"],
    )
    client = session.client("ecs")
    run_task_response = client.run_task(
        cluster=os.environ["CLUSTER_ID"],
        taskDefinition=os.environ["PURPLEAIR_TASK_ARN"],
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
        "--recipients",
        metavar="EMAIL@DOMAIN",
        nargs="+",
        help="The recipients to send the email to. If not provided, then no email is sent.",
        required=True,
    )

    args = parser.parse_args()
    return args


if __name__ == "__main__":
    main()
