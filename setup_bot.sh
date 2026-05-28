#! /usr/bin/env bash

set -e

# Install dependencies
echo "Creating venv"
python3 -m venv venv

echo "Activating venv"
. venv/bin/activate

echo "Installing dependencies from requirements.txt"
python3 -m pip install -q -r requirements.txt 

sudo apt install chromium

python3 -m playwright install --with-deps
playwright install-deps
playwright install 

# Setup booking_bot so it starts as a systemd service
echo "Setting up booking_bot service..."

sudo cp files/booking_bot.service /etc/systemd/system/
sudo cp files/booking_bot.timer /etc/systemd/system/

sudo systemctl enable booking_bot.timer

sudo systemctl start booking_bot.timer
sudo systemctl status booking_bot.timer

sudo apt-get install libatk1.0-0 libatk-bridge2.0-0 libxkbcommon0 libpango-1.0-0 libxdamage1 libatspi2.0-0