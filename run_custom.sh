#!/bin/sh

# Script that runs in Docker container
quant_scrape /quantscraper/shared/custom_scrape.ini
quant_preprocess /quantscraper/shared/custom_preprocess.json
