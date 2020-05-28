#!/bin/sh

# Echoes version number, found in setup.py 
cat setup.py | grep version | grep '\([0-9]\+\.\?\)\{3\}' -o
