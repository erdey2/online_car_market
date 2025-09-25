#!/usr/bin/env bash

# Install Graphviz dev files
apt-get update
apt-get install -y graphviz libgraphviz-dev pkg-config

# Upgrade pip
pip install --upgrade pip

# Install Python packages
pip install -r requirements/local.txt

# Collect static files and run migrations
python manage.py collectstatic --noinput
python manage.py migrate

