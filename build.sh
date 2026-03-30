#!/bin/bash
# Vercel Python build script

# Install dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Print Python and pip versions
python --version
pip list
