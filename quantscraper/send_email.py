"""
    send_email.py
    ~~~~~~~~~~~~~

    Sends email containing scraping summary.
"""

import sys
import traceback
import argparse
import os
import logging
import boto3
from botocore.exceptions import ClientError

from quantscraper import utils
import quantscraper.cli as cli


def main():
    args = parse_args()

    # Just using same setup functions as cli.py here.
    # Don't think would be appropriate to refactor these functions into the
    # utils.py module, as these are script functions, rather than library
    # functions associated with the collection of air quality data
    try:
        cli.setup_loggers()
    except utils.SetupError:
        logging.error("Error in setting up loggers.")
        logging.error(traceback.format_exc())
        logging.error("Terminating program")
        sys.exit()

    # TODO Refactor this into utils functions, or Email class

    # Parse JSON environment variable into separate env vars
    try:
        vars = utils.parse_JSON_environment_variable("EMAIL_CREDS")
    except utils.SetupError:
        logging.error(
            "Error when initiating environment variables, terminating execution."
        )
        logging.error(traceback.format_exc())
        sys.exit()

    for k, v in vars.items():
        os.environ[k] = v

    # Read HTML file
    try:
        with open(args.file, "r") as infile:
            body_html = infile.read()
    except FileNotFoundError:
        logging.error(
            "Error. Cannot open HTML file '{}'. Terminating executation.".format(
                args.file
            )
        )
        return

    try:
        sender = os.environ["EMAIL_SENDER_ADDRESS"]
    except KeyError:
        logging.error(
            "Error: no EMAIL_SENDER_ADDRESS environment variable. Set this to the email address that is sending the email."
        )
        return

    try:
        identity_arn = os.environ["IDENTITY_ARN"]
    except KeyError:
        logging.error(
            "Error: no IDENTITY_ARN environment variable. Set this to ARN of the identity that is authorised to send emails from the EMAIL_SENDER_ADDRESS"
        )
        return

    subject = "QUANT scraping summary - {}".format(args.date)
    charset = "UTF-8"
    # The email body for recipients with non-HTML email clients.
    body_text = (
        "Unable to render HTML. Please open the following content in a web browser\r\n"
        "{}"
    ).format(body_html)

    client = boto3.client("ses")
    try:
        logging.info("Attemping to send email...")
        response = client.send_email(
            Destination={"ToAddresses": args.recipients,},
            Message={
                "Body": {
                    "Html": {"Charset": charset, "Data": body_html,},
                    "Text": {"Charset": charset, "Data": body_text,},
                },
                "Subject": {"Charset": charset, "Data": subject,},
            },
            Source=sender,
            SourceArn=identity_arn,
            ReturnPath=sender,
            ReturnPathArn=identity_arn,
        )
    except ClientError as e:
        logging.error(e.response["Error"]["Message"])
    else:
        logging.info("Email sent with message ID:"),
        logging.info(response["MessageId"])


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
        "--date",
        metavar="DATE",
        help="The date that scraping was run for. Must be in the format YYYY-mm-dd.",
        required=True,
    )

    parser.add_argument(
        "--file",
        metavar="FILE",
        help="The location of the HTML file that will be sent.",
        required=True,
    )

    parser.add_argument(
        "--recipients",
        metavar="EMAIL@DOMAIN",
        nargs="+",
        help="The recipients to send the email to.",
        required=True,
    )

    args = parser.parse_args()
    return args


if __name__ == "__main__":
    main()
