#!/bin/sh

# Script that runs in Docker container
quant_scrape daily_scrape.ini
quant_preprocess daily_preprocessing.json
