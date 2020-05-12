#!/bin/sh

# Builds docker image of latest release
# TODO How to automatically obtain release number?
docker build -t wacl/quantscraper:0.2.0 .
