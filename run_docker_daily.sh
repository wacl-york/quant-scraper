#!/bin/sh

# Runs a custom scrape on Docker
docker run --rm -v $(pwd)/shared:/quantscraper/shared wacl/quantscraper:0.2.0 /quantscraper/run_daily.sh
