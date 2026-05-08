#! /usr/bin/env bash

set -e

# Install dependencies
echo "Creating venv"
python3 -m venv venv

echo "Activating venv"
. venv/bin/activate

echo "Installing dependencies from requirements.txt"
python3 -m pip install -q -r requirements.txt 

# Setup booking_bot so it starts as a systemd service
echo "Setting up booking_bot service..."

sudo cp files/booking_bot.service /etc/systemd/system/
sudo cp files/booking_bot.timer /etc/systemd/system/

sudo systemctl enable booking_bot.timer

sudo systemctl start booking_bot.timer
sudo systemctl status booking_bot.timer
