![Python application](https://github.com/wacl-york/quant-scraper/workflows/Python%20application/badge.svg?branch=main)
![Test coverage](https://webfiles.york.ac.uk/WACL/QUANT/QUANTscraper/resources/coverage.svg)

# quant-scraper

Scrapes data from the websites of air quality instrumentation system manufacturers for the QUANT project.

# Setting up scheduled scraping

QUANTScraper runs on AWS Fargate and is currently configured to run in an account associated with the QUANT project.
The app is deployed through a GitHub Action that is triggered by a pull-request into the `main` branch of this repository.

## Creating deploy IAM user

An IAM user that handles deployment needs to be created.
Follow the steps listed on the [University's documentation](https://wiki.york.ac.uk/display/AWS/AWS%3A+Github+Actions) to create a User that initially just belongs to the University's `GithubActionsDeployments` group, this is sufficient for providing the permissions to deploy CloudFront Stacks.

Permissions will also need to be added to this user to allow it to push images to the ECR repository.
A minimal working example is shown below, remember to substitute in the `awsaccountid`.

Finally, save the access token and its id somewhere safe.

```
{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Sid": "AllowPush",
            "Effect": "Allow",
            "Action": [
                "ecr:GetDownloadUrlForLayer",
                "ecr:BatchGetImage",
                "ecr:BatchCheckLayerAvailability",
                "ecr:PutImage",
                "ecr:InitiateLayerUpload",
                "ecr:UploadLayerPart",
                "ecr:CompleteLayerUpload"
            ],
            "Resource": [
                            "arn:aws:ecr:eu-west-1:<awsaccountid>:repository/wacl/quantscraper",
                            "arn:aws:ecr:eu-west-1:<awsaccountid>:repository/wacl/purpleair-conversion"
                        ]
        },
        {
            "Sid": "GetAuthToken",
            "Effect": "Allow",
            "Action": "ecr:GetAuthorizationToken",
            "Resource": "*"
        }
    ]
}
```

## Deploying

Create (or update if already present) the following 3 Secrets in this GitHub repository:

  - `AWS_ACCESS_KEY_ID`: from the deploy IAM user created above
  - `AWS_SECRET_ACCESS_KEY`: from the deploy IAM user created above
  - `AWS_USER_ID`: The AWS account ID where the app is to be deployed

The scraping app can now be deployed by accepting a new pull request into `main`.
This will either create a new Stack if one doesn't already exist or update the existing one, and then push the latest Docker image to ECR.

## Populate Secrets

Before the app can run, the scraping secrets on AWS need to be populated.
Open `Secrets Manager` in the AWS console to see 3 secrets with placeholder values - these should be self-explanatory and are all available in LastPass.

Take care when copying values over; it is best to use the `plaintext` editor rather than the GUI `Secret key/value` GUI.
There are 2 reasons for this; firstly you can copy a whole JSON secret in one motion with the `plaintext` editor rather than having to copy each key/value pair at a time, and secondly the GUI escapes special characters such as `\n`.

## Authenticating emails

It is unlikely that any the automated emails will need any configuration, but for reference the process is listed here.

The summary emails will be sent from the address `quant_scraper.york.ac.uk`, which is authorised to send emails through a University *Identity*.
The authentication identity is specified by an ARN in the `EMAIL_CREDS` JSON secret and should have been populated in the previous step.
Nothing else needs to be done to authorise emails from the **sending** end except if the app is being deployed on a new AWS account ID, in which case put a Footprint in to Systems so that they can register the new account at their end.

Any addresses that are going to **receive** emails must be verified through the SES webpage.
This involves sending a verification email to the desired account and clicking the included link to confirm verification.

The project Google Group has already been verified on the current AWS project account so this step shouldn't be necessary again, although it is worth bearing in mind for future projects or if the AWS account changes.
NB: Google Groups by default cannot receive emails sent externally of the `york.ac.uk` domain, and must have the `Post` permission extended to include *Anyone on the web*.
This allows the Group address to receive the verification request, although the `Post` permission can (and should) be reverted back to *All organisation members* afterwards and it will still be able to receive the summary emails.

## Scheduled scrapes

By default, a full scrape of all devices from the previous day is run at 09:00 GMT with the resulting data uploaded to Google Drive and a summary email sent to `quant-group@york.ac.uk`.
If this doesn't run successfully, look in the `/ecs/QUANT-scraping-logs` log group in CloudWatch.

The scheduled scraping parameters are defined in the `cloudformation/main.yml` template, and can also be changed in the AWS console.
The available flags can be viewed by running `python entry.py --help` 

For example, Seba has requested that not all devices are included in the pre-processed `Analysis` CSV files, which is specified through the `--preprocess-devices` flag.

# Running ad-hoc scraping tasks

As well as running the daily scrape, it is also desirable to be able to run one-off jobs every now and then.
This is also run through Fargate, with events being triggered by `boto` calls.

## Setup

The CloudFormation Stack setup an IAM user called `QUANT_IAM_RunAdHoc` that has the required permissions to launch these jobs.

To use it, generate access tokens (in the `Security credentials` tab of the User's Console page) and save them to `~/.aws/credentials` under a profile called `QUANTRunAdHocTask`.

Then, create a file called `run.env` with the following values:

```
CLUSTER_ID=QUANTCluster
AWS_TASK_PROFILE=QUANTRunAdHocTask
QUANT_TASK_ARN=arn:aws:ecs:eu-west-1:<awsaccountid>:task-definition/QUANTTasks
SUBNET_1=<subnet1id>
SUBNET_2=<subnet2id>
SECURITY_GROUP=<securitygroupid>
AWS_CLI_REGION=eu-west-1
```

`<subnet1id>` and `<subnet2id>` are the `Subnet ID` column values from the table of available subnets where the name is `QUANT Subnet 1/2` (navigate to the `VPC` page then click `Subnets` in the left-hand navigation panel).
Also from the `VPC` page, click `Security Groups` in the navigation panel and use the `Security group ID` column value where the name is `QUANT SecurityGroup` for `<securitygroupid>`.

Finally, download the `run_scrape.py` script from this repository and install `boto3` if it hasn't been already.

## Submitting jobs

`run_scrape.py` provides an interface to the Docker image with the same command line arguments and uses `boto` to launch the task.
See `python run_scrape.py --help` for all the available options.

# Running the scraper locally

The scraping can also be run locally rather than from AWS.
This requires installing the `quantscraper` Python package in a local environment and interfacing with it using command line arguments and configuration files.

## Installation

A recent installation of Python (>= 3.7) needs to be available.
This can be installed manually, or through the `conda` environment manager.

Conda can be installed from their website: [https://docs.conda.io/en/latest/](https://docs.conda.io/en/latest/). 
If it is only going to be used for this project, I would recommend the [`miniconda` version](https://docs.conda.io/en/latest/miniconda.html), as it is more minimalist and just contains libraries required to run Python.

A `conda` environment can be created with Python 3.7 through the following command.

`conda create --name <ENVNAME> python=3.7`

And can be used through

`conda activate <ENVNAME>`

The latest stable version of the Python package `quantscraper` can then be installed from GitHub by using the following command.

`pip install git+https://github.com/wacl-york/quant-scraper.git@main`

## Running the scraper 

The installation processes places an executable called `quant_scrape` in the user's `PATH`.

By default, the scraper will run for all available instruments over the 24 hour period from midnight of the previous day to 1 second before midnight of the current day.
A summary of the scraping is output to `stdout`, while a log will be displayed on `stderr`.
Command line arguments allow for the specification of the instruments to scrape and the timeframe, in addition to uploading the resultant data to Google Drive and saving an HTML summary table.

Run `quant_scrape --help` to see the available options.

## Running the pre-processing script

In addition to the CLI scraping program there is a pre-processing script that takes the cleaned and validated data as stored by the `quant_scrape` command, and organises it into a format suitable for immediate analysis.
In particular, it converts the data into a wide format with 1 file per manufacturer and resamples all time-series to 1 minute resolution.

The program is run using the `quant_preprocess` command; see `quant_preprocess --help` for the available options.

# Contributing to development

To contribute to the development, firstly clone this repository:

`git clone https://github.com/wacl-york/quant-scraper.git`

## conda setup

The development environment can be replicated by creating a new `conda` environment from the supplied configuration file.

`conda env create -f environment.yml`

This will create a `conda` environment called `quant-scraper` and install all the dependencies.
If it fails to install all dependencies then the environment will still be created but without all the required libraries, which can be installed as per the `Manual` instructions below.

Use this environment by entering

`conda activate quant-scraper`

## Manual setup

Optionally, the dependencies can be installed manually.
The scraper runs on Python 3.7 or higher, and requires a number of packages to be installed from `pip`:

  - `boto3`
  - `bs4`
  - `google-api-python-client`
  - `google-auth-httplib2`
  - `google-auth-oauthlib`
  - `pandas`
  - `numpy`
  - `python-dotenv`
  - `requests`

In addition to these packages, there is a [Python wrapper](https://github.com/quant-aq/py-quantaq) for accessing QuantAQ's API, which can be installed from GitHub using the following command:

`pip install git://github.com/quant-aq/py-quantaq.git@v0.3.0#egg=quantaq`

Finally, the [`Black` formatter](https://github.com/psf/black) is used in development as a pre-commit hook to ensure consistent formatting across source files. 
It can also be installed through `pip`.

## Testing

All unit tests can be run using the following command:

`coverage run -m unittest discover -s tests -b`

Test coverage can be viewed by running `coverage report` afterwards.

## Running the program during development

To run the program scripts while developing, install it locally in editable mode with:

`pip install -e .`

This will add the appropriate package imports to your `PYTHONPATH` and will update them when needed.

You can then run the main scripts with `python quantscraper/cli.py` or `python quantscraper/daily_preprocessing.py`.
