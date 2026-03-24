#!/usr/bin/env bash
# exit on error
set -o errexit

# Install torch-cpu and torchvision-cpu to save ~1GB of storage
echo "Installing CPU-only PyTorch..."
pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install the rest of the requirements
pip install -r requirements.txt

# Django commands
python manage.py collectstatic --no-input
python manage.py migrate
