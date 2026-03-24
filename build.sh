#!/usr/bin/env bash
# exit on error
set -o errexit

export CMAKE_ARGS="-DCMAKE_POLICY_VERSION_MINIMUM=3.5"
pip install -r requirements.txt

python manage.py collectstatic --no-input
python manage.py migrate
