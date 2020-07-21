![Python application](https://github.com/wacl-york/QUANTscraper/workflows/Python%20application/badge.svg?branch=master)
![Test coverage](https://webfiles.york.ac.uk/WACL/QUANT/QUANTscraper/resources/coverage.svg)

# QUANTscraper

Scrapes data from the websites of air quality instrumentation system manufacturers for the QUANT project.

# Running QUANTscraper on AWS

## Setup

### Creating CloudFormation Stack

A CloudFormation template of all the required resources is provided in the file `aws_cloudformation.template`. 

Firstly, create a Stack from this template in the `CloudFormation` website (or via the CLI), passing in the following values:

  - Stack name: `QUANTScrapingStack`
  - Parameters:
    - `EmailRecipient`: An email address that the automated summarise will be sent to, preferably a mailing list.
    - `TaskFamily`: Leave as default.
  - Tags:
    - `group`: `RESEARCH`
    - `project`: `quant`
    - `status`: `prod`
    - `pushed_by`: `manual`
    - `defined_in`: `cloudformation`
    - `repo_name`: `wacl-york/quantscraper`
    - `user`: `sl561`
    - `team`: `rhpc`

Don't forget to click the box in `Capabilities` to acknowledge that CloudFormation is going to create IAM resources.

The stack contains all the necessary AWS resources to run the data scraping, although a few additional bits of configuration are required before the program is ready to be run.

### Populate Secrets

Open `Secrets Manager` in AWS and you will notice there are 3 secrets with placeholder values.
These should be self-explanatory and are all available in LastPass.

Take care when copying values over; it is best to use the `plaintext` editor rather than the GUI `Secret key/value` GUI.
There are 2 reasons for this; firstly you can copy a whole JSON secret in one motion with the `plaintext` editor rather than having to copy each key/value pair at a time, and secondly the GUI escapes special characters such as `\n`, which is particularly frustrating when copying over the Google Service Account credentials JSON.

### Create IAM credentials

The Stack includes 2 IAM users:

  - `QUANT_IAM_ECR`: Can upload Docker images to ECR
  - `QUANT_IAM_RunAdHoc`: Can run one-off tasks from a local machine using `boto3`

Before these IAM users can be used, access tokens need to be generated and saved to your local machine.

Go into the `Security credentials` tab on each user's page and click `Create access key`. 
Download the resulting `access key id` and `secret access key` and save them into `~/.aws/credentials` under the profiles `QUANTECRPush` and `QUANTRunAdHocTask` respectively.

### Push Docker image to repository

The `Makefile` includes the functionality to push images to the ECR repository.
Environment variables need to be configured before the first push.

Create a file called `deploy.env` in your working directory with the following values:

```
APP_NAME=<reponame>
DOCKER_REPO=<userid>.dkr.ecr.<awsregion>.amazonaws.com
AWS_CLI_REGION=<awsregion>
AWS_ECR_PROFILE=QUANTECRPush
```

`<reponame>` is the repository name, found in the ECR table as the string in the `Repository Name` column.

`<userid>` is the numeric user id found in the same row of the table as the first part of the `URI` column.

`<awsregion>` is the region identifier for the region the account is based in.

`QUANTECRPush` is the IAM profile setup in the previous step.

**NB: You don't have to use a deploy.env file, as long as these 4 environment variables are available to the Makefile**

Once this has been setup, run `make release` to build the latest image, tag it, and push it to the repository.

### Authenticating emails

The summary emails will be sent from the address `quant_scraper.york.ac.uk`, which is authorised to send emails through a University *Identity*.
This is specified by an ARN in the `EMAIL_CREDS` JSON secret, which is stored on LastPass and should have been used to populate the initial empty Secret in the first step of this setup process.
Nothing else needs to be done to authorise emails from the **sending** end.

Any addresses that are going to **receive** emails must be verified through the SES webpage.
This involves sending a verification email to the desired account and clicking the included link to confirm verification.

**The project Google Group has already been verified on the current AWS project account so this step shouldn't be necessary again, although it is worth bearing in mind for future projects or if the AWS account changes.**

NB: Google Groups by default cannot receive emails sent externally of the `york.ac.uk` domain, and must have the `Post` permission extended to include *Anyone on the web*.
This allows the Group address to receive the verification request, although the `Post` permission can (and should in many cases) be reverted back to *All organisation members* afterwards and it will still be able to receive the summary emails.

### Configuration to run ad-hoc scraping tasks

If you wish to run one-off scraping jobs from the command line of a local machine then more environment variables will need creating.

Create a file called `run.env` with the following values:

```
CLUSTER_ID=<clusterid>
AWS_TASK_PROFILE=QUANTRunAdHocTask
QUANT_TASK_ARN=<taskArn>
SUBNET_1=<subnet1id>
SUBNET_2=<subnet2id>
SECURITY_GROUP=<securitygroupid>
AWS_CLI_REGION=<awsregion>
```

`QUANTRunAdHocTask` is the name of the profile in `~/.aws/credentials` that should have been populated previously with the access keys.

`<clusterid>` is the name of the Cluster, which by default is `QUANTCluster` (check this on the Clusters page, accessed from the ECS page).

`<taskArn>` takes the form `arn:aws:ecs:<awsregion>:<userid>:task-definition/QUANTTasks`, where `QUANTTasks` is the default task family name and `<userid>` and `<awsregion>` are the same as when setting up the ECR env vars.

`<subnet1id>` and `<subnet2id>` are the `Subnet ID` column values from the table of available subnets where the name is `QUANT Subnet 1/2` (navigate to the `VPC` page then click `Subnets` in the left-hand navigation panel).

Also from the `VPC` page, click `Security Groups` in the navigation panel and use the `Security group ID` column value where the name is `QUANT SecurityGroup` for `<securitygroupid>`

## Scheduled scrapes

By default, a full scrape of all devices from the previous day is run at 13:00 UTC, with the resulting data uploaded to Google Drive.
This can be configured by clicking the `Scheduled Tasks` tab of the Cluster page (in itself accessed from the ECS page).
To change the scraping parameters, add the appropriate flags to `Command override`.
The available flags can be viewed by running `python entry.py --help`.

For example, Seba has requested that not all devices are included in the pre-processed `Analysis` CSV files, which is specified through the `--preprocess-devices` flag.

**NB: sometimes just changing the CRON specification can remove the command override parameters, make sure to back them up before modifying any part of the scheduled task.**

## One-off scraping runs

To run ad-hoc scrapes, the `run_scrape.py` provides a wrapper around running the container on Fargate, passing in command-line arguments to it.
Setup the package dependencies as described in the following section and ensure the values in `run.env` are correct and that you have downloaded `run_scrape.py` (it isn't yet bundled into the package).

Then simply run `python run_scrape.py --help` to see the available options.

# Running QUANTscraper locally

The scraping can also be run locally rather than from AWS.
This requires installing the `quantscraper` Python package in a local environment and interfacing with it using command line arguments and configuration files.

## Installation

### Python 3.7

A recent installation of Python (>= 3.7) needs to be available.
This can be installed manually, or through the `conda` environment manager.

Conda can be installed from their website: [https://docs.conda.io/en/latest/](https://docs.conda.io/en/latest/). 
If it is only going to be used for this project, I would recommend the [`miniconda` version](https://docs.conda.io/en/latest/miniconda.html), as it is more minimalist and just contains libraries required to run Python.

A `conda` environment can be created with Python 3.7 through the following command.

`conda create --name <ENVNAME> python=3.7`

And can be used through

`conda activate <ENVNAME>`

### `quantscraper` installation

Once a suitable version of Python has been made available, the latest stable version of `quantscraper` can be installed from GitHub by using the following command.

`pip install git+https://github.com/wacl-york/QUANTscraper.git@master`

## Running the scraper 

The installation processes places an executable called `quant_scrape` in the user's `PATH` and is run with the following command.

`quant_scrape`

By default, the scraper will run for all available instruments over the 24 hour period from midnight of the previous day to 1 second before midnight of the current day.
A summary of the scraping is output to `stdout`, while a log will be displayed on `stderr`.
Command line arguments allow for the specification of the instruments to scrape and the timeframe, in addition to uploading the resultant data to Google Drive and saving an HTML summary table.

Run `quant_scrape --help` to see the available options.

### Configuration

The `quant_scrape` command requires a configuration file called `config.ini` to be present in the directory where the executable is called from.
This file provides parameters for the scraping; `resources/example.ini` shows the required format.

### Manufacturer and device specification

In addition, it requires the presence of a file called `devices.json` in the working directory.
This file maps the relationship between the manufacturers and the devices in the study.
Each entry in the `manufacturers` list reflects an air quality instrumentation company included in the study, with the `properties` object providing keyword-value properties that must be completed before running the program.
The `fields` list defines the measurands recorded by devices from this company, represented by an object containing a human readable label (`id`), an ID used to refer to this measurand by the company in the downloaded data (`webid`), and a `scale` parameter that is multiplied by the raw value.
The `devices` list holds a record of the physical instruments installed from this company, represented by an object containing a human readable label (`id`), an ID used to refer to this device by the company on their system (`webid`), and a description of where the device is installed (`location`).

The example file `resources/example_devices.json` shows the required layout.

## Running the pre-processing

In addition to the CLI scraping program there is a pre-processing script, which takes the cleaned and validated data as stored by the `quant_scrape` command, and organises the data into a format suitable for analysis.

In particular, it converts the data from being saved in long format with 1 file per device, into wide format with 1 file per manufacturer.
It also resamples the time-series so that the air quality data from all manufacturers is saved at the same sampling rate.

The program is run using the `quant_preprocess` command that should be added to the `PATH` as part of the installation. 

As with the scraping program, it requires the presence of `devices.json` in the working directory to define the manufacturers and devices included in the study.
It also requires its own separate configuration file to be present in the working directory: `preprocessing.ini`.
An example is provided by `resources/example_preprocessing.ini`.

By default the program pre-processes the previous day's cleaned data for all available instruments, although this behaviour can be configured by setting a YYYY-mm-dd formatted date to the `--date` argument and specifying the devices with the `--devices` flag.
Furthermore, the resultant processed data can be uploaded to Google Drive by setting the `--upload` flag.
Run `quant_preprocess --help` to see the available options.

# Contributing to development

To contribute to the development of `quantscraper`, firstly clone this repository:

`git clone https://github.com/wacl-york/QUANTscraper.git`

## conda setup

The development environment can be replicated by creating a new `conda` environment from the supplied configuration file.

`conda env create -f environment.yml`

This will create a `conda` environment called `QUANTscraper` and install all the dependencies.
If it fails to install all dependencies then it should create an empty environment called `QUANTscraper`, which can be activated as below with the remaining dependencies installed as per the `Manual` instructions below.

Use this environment by entering

`conda activate QUANTscraper`

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

`pip install git+https://github.com/quant-aq/py-quantaq.git`

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
