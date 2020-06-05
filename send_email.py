"""
    send_email.py
    ~~~~~~~~~~~~~

    Sends email containing scraping summary.
"""

import argparse
import os
import boto3
from botocore.exceptions import ClientError
from dotenv import load_dotenv


def main():

    args = parse_args()

    # Load environment parameters containing AWS runtime details
    env_fn = "email.env"
    load_dotenv(dotenv_path=env_fn)

    # Read HTML file
    try:
        with open(args.file, "r") as infile:
            body_html = infile.read()
    except FileNotFoundError:
        print(
            "Error. Cannot open HTML file '{}'. Terminating executation.".format(
                args.file
            )
        )
        return

    try:
        sender = os.environ["EMAIL_SENDER_ADDRESS"]
    except KeyError:
        print(
            "Error: no EMAIL_SENDER_ADDRESS environment variable. Set this to the email address that is sending the email."
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
        print("Attemping to send email...")
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
            ReturnPath=sender,
        )
    except ClientError as e:
        print(e.response["Error"]["Message"])
    else:
        print("Email sent! Message ID:"),
        print(response["MessageId"])


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
