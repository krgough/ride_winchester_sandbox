"""

pip install playwright
playwright install chromium

"""

from argparse import ArgumentParser
from enum import Enum
import json
import logging
import os
from pathlib import Path
import sys
import time
import requests

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

LOGGER = logging.getLogger(__name__)

load_dotenv(Path(__file__).parent / ".env")  # Load environment variables from .env file


ENV_VARS = {
    "USERNAME": os.getenv("RW_USERNAME", None),
    "PASSWORD": os.getenv("RW_PASSWORD", None),
    "NOTIFICATION_TOPIC": os.getenv("NOTIFICATION_TOPIC", None),
    "NOTIFICATION_TEST_TOPIC": os.getenv("NOTIFICATION_TEST_TOPIC", None)
}

if not all(ENV_VARS.values()):
    missing_vars = [key for key, value in ENV_VARS.items() if not value]
    LOGGER.error("The following environment variables are missing from the .env file: %s", ", ".join(missing_vars))
    sys.exit(1)


class Paces(Enum):
    """ Enum for the different pace options on the booking form. """
    EASY = "ipaces1"
    EASY_PLUS = "ipaces2"
    MEDIUM = "ipaces3"
    MEDIUM_PLUS = "ipaces4"
    FREE_FORMAT = "ipaces5"


class Days(Enum):
    """ Enum for the different days of the week options on the booking form. """
    TUESDAY = "tues"
    WEDNESDAY = "weds"
    THURSDAY = "thurs"
    FRIDAY = "fri"
    SATURDAY = "sat"
    SUNDAY = "sun"


class RideStates(Enum):
    """ Enum for the different ride states that can be scraped from the ride details page. """
    AVAILABLE = "Available to book"
    NOT_AVAILABLE = "Ride not available yet"
    FULL = "RIDE FULL"
    UNKNOWN = "Unknown"


PREVIOUSLY_CHECKED_RIDES_FILE = "ride_winchester/booking_bot/previously_checked_rides.txt"


def get_args():
    """ Get command line arguments for the script. """
    parser = ArgumentParser(description="Playwright script to automate notify/book rides on Winchester CTC website.")
    parser.add_argument(
        "--headless",
        action="store_true",
        default=False,
        help="Run browser in headless mode (no UI)."
    )
    parser.add_argument(
        "-a", "--auto-book",
        action="store_true",
        default=False,
        help="Automatically book available rides and add to wait list for full rides."
    )

    # split comma separated values and convert to list of enums
    parser.add_argument(
        "-d", "--days",
        type=lambda s: [Days[day.strip().upper()] for day in s.split(",")],
        help="Comma separated days of the week to filter rides by. E.g. --days Tuesday,Thursday,Saturday",
        required=True
    )

    parser.add_argument(
        "-p", "--paces",
        type=lambda s: [Paces[pace.strip().upper()] for pace in s.split(",")],
        help="Comma separated pace options to filter rides by. EASY, EASY_PLUS, MEDIUM, MEDIUM_PLUS, FREE_FORMAT",
        required=True
    )
    return parser.parse_args()


def login(page):
    """ Navigate to login page and perform login using credentials from .env file. """
    # Go to the login page and enter creds
    LOGGER.info("Navigating to login...")
    page.goto("https://winchesterctc.org.uk/RW/Dev/user_login.php")

    # Fill in the login creds
    page.fill('input[name="userid_email"]', ENV_VARS["USERNAME"])
    page.fill('input[name="pwd"]', ENV_VARS["PASSWORD"])

    # Click the login button and wait for the page to load
    page.get_by_role("button", name="Log In").click()
    page.wait_for_load_state("networkidle")
    LOGGER.info("Logged in successfully.")


def set_checkbox(page, checkbox_id, set_checked=True):
    """ Set a checkbox by ID if it's not already in the desired state """
    is_checked = page.locator(f"#{checkbox_id.value}").is_checked()

    if set_checked and not is_checked:
        LOGGER.info("Selecting %s...", checkbox_id)
        page.locator(f"#{checkbox_id.value}").set_checked(True)
        page.wait_for_function(f'document.querySelector("#{checkbox_id.value}").checked === true')

    elif not set_checked and is_checked:
        LOGGER.info("Deselecting %s...", checkbox_id)
        # Convoluted way to uncheck - this was all that worked
        page.locator(f"#{checkbox_id.value}").set_checked(False)
        page.evaluate(f"""
            const el = document.getElementById('{checkbox_id.value}');
            if (el) {{
                // Save the function for later
                const originalAttr = el.getAttribute('onchange');
                el.removeAttribute('onchange');

                // Change state without triggering the "fight"
                el.checked = false;

                // Put the function back and call it manually
                el.setAttribute('onchange', originalAttr);
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
        """)


def set_ride_filters(page, day_selections, pace_selections):
    """ Set the ride filters on the rides list page based on the selected days and paces. """
    # Check what days are selected
    for day in Days:
        set_checkbox(page, day, set_checked=day in day_selections)
        # time.sleep(0.5)  # Add a small delay to allow the page to update after each checkbox change

    for pace in Paces:
        set_checkbox(page, pace, set_checked=pace in pace_selections)
        # time.sleep(0.5)  # Add a small delay to allow the page to update after each checkbox change

    time.sleep(5)  # Wait a bit for the page to update after changing filters


def inspect_ride(page, ride_id):
    """ Inspect a given ride
    Select a ride from the dropdown
    scrape the wanted details
    return to the rides list page
    """

    # select_option automatically triggers the 'change' event
    # page.select_option("select#xx", value=ride_id)

    # page.goto("https://winchesterctc.org.uk/RW/Dev/calendarView.php")  # Ensure we're on the rides list page
    # page.wait_for_load_state("networkidle")

    # page.goto(f"https://winchesterctc.org.uk/RW/index.php?ride={ride_id}")
    # page.wait_for_load_state("networkidle")
    # page.wait_for_selector("table.centertable")

    LOGGER.info("Inspecting Ride ID: %s", ride_id)

    post_data = {"listsel": ride_id}
    page.evaluate("""(data) => {
        const form = document.createElement('form');
        form.method = 'POST';
        form.action = 'ridedetails.php';

        for (const key in data) {
            const input = document.createElement('input');
            input.type = 'hidden';
            input.name = key;
            input.value = data[key];
            form.appendChild(input);
        }

        document.body.appendChild(form);
        form.submit();
    }""", post_data)

    # Now wait for the table to load
    page.wait_for_selector("table.centertable")

    # Scrape the ride content

    # Find table
    table_locator = page.locator("table.centertable")  # Use the actual ID or class
    rows = table_locator.locator("tr").all()

    ride_details = {"ride_id": ride_id}
    for row in rows:
        # Get the cells in this row
        cells = row.locator("td").all_inner_texts()

        if len(cells) == 2:
            key = cells[0].strip()
            value = cells[1].strip()
            ride_details[key] = value

    LOGGER.info(json.dumps(ride_details, indent=2))

    # navigate back to the rides list if needed (or just select the next ride)
    # page.click('a.linkbutton:has-text("Back to Rides List")')
    # page.wait_for_load_state("networkidle")

    return ride_details


def load_previously_checked_rides(filename):
    """ Load the list of previously checked rides """
    with open(filename, "r", encoding="utf-8") as f:
        return [line.strip() for line in f.readlines()]


def add_to_previously_checked_rides(ride_id):
    """ Add a ride ID to the list of previously checked rides """
    with open(PREVIOUSLY_CHECKED_RIDES_FILE, "a", encoding="utf-8") as f:
        f.write(f"{ride_id}\n")


def remove_old_rides_from_previously_checked_rides(filename, valid_ride_ids):
    """ Remove ride IDs from the previously checked rides file if they are no longer valid """
    with open(filename, "r", encoding="utf-8") as f:
        checked_rides = [line.strip() for line in f.readlines()]
        updated_checked_rides = [ride_id for ride_id in checked_rides if ride_id in valid_ride_ids]

    with open(filename, "w", encoding="utf-8") as f:
        for ride_id in updated_checked_rides:
            f.write(f"{ride_id}\n")


def book_ride(page, ride_id):
    """ Book a ride by clicking the book button on the ride details page """
    LOGGER.info("Booking ride %s...", ride_id)
    page.goto(f"https://winchesterctc.org.uk/RW/Dev/ridedetails.php?ride={ride_id}")
    page.wait_for_selector("#bookbutton")
    # page.click("#bookbutton")
    page.wait_for_load_state("networkidle")
    LOGGER.info("Ride %s booked successfully.", ride_id)


def add_to_wait_list(page, ride_id):
    """ Add to wait list by clicking the wait list button on the ride details page """
    LOGGER.info("Adding to wait list for ride %s...", ride_id)
    page.goto(f"https://winchesterctc.org.uk/RW/Dev/ridedetails.php?ride={ride_id}")
    page.wait_for_selector("#waitingbutton")
    # page.click("#waitingbutton")
    page.wait_for_load_state("networkidle")
    LOGGER.info("Added to wait list for ride %s successfully.", ride_id)


def notify_ride(ride):
    """ Notify the user about a new ride - this is just a placeholder for now """
    LOGGER.info(
        "Notifying user: New ride found! Ride Data: %s",
        json.dumps(ride, indent=2)
    )
    url = f"https://ntfy.sh/{ENV_VARS['NOTIFICATION_TOPIC']}"
    rw_url = f"https://www.winchesterctc.org.uk/RW/CalendarDetailsV2.php?ride={ride['ride_id']}"
    title = f"New ride found: {ride['Date']}, {ride['Description']}"
    headers = {
        "Actions": f"View, View Ride, url={rw_url}",
        "Priority": "5",
        "Title": title
    }
    resp = requests.post(
        url=url,
        headers=headers,
        data="New ride found! Click to view",
        timeout=5
    )
    print(resp.status_code, resp.text)


def notify_booking_or_waitlist(ride, action):
    """ Notify the user about a new booking or waitlist - this is just a placeholder for now """
    LOGGER.info(
        "Notifying user: Successfully %s ride! Ride Data: %s",
        action,
        json.dumps(ride, indent=2)
    )
    url = f"https://ntfy.sh/{ENV_VARS['NOTIFICATION_TEST_TOPIC']}"
    title = f"Successfully {action} ride: {ride['Date']}, {ride['Description']}"
    headers = {
        "Priority": "5",
        "Title": title
    }
    resp = requests.post(
        url=url,
        headers=headers,
        data=f"Successfully {action} ride!",
        timeout=5
    )
    print(resp.status_code, resp.text)


def main():
    """ Main function to run the Playwright script """

    args = get_args()

    # Load the list of previously checked rides to avoid duplicate notifications
    previously_checked_rides = load_previously_checked_rides(filename=PREVIOUSLY_CHECKED_RIDES_FILE)

    with sync_playwright() as p:
        # Launch browser (headless=False so you can see the login happen)
        browser = p.chromium.launch(executable_path="/usr/bin/chromium-browser", headless=args.headless)
        # browser = p.chromium.launch(headless=args.headless)
        context = browser.new_context()
        page = context.new_page()

        # Go to the login page and enter creds
        login(page)

        # Set the day and pace filters
        set_ride_filters(page, args.days, args.paces)

        # Scrape the list of all Ride IDs and get the details for each ride
        ride_values = page.eval_on_selector_all("select#xx option", "options => options.map(o => o.value)")
        LOGGER.info("Found %d rides.", len(ride_values))
        rides = [inspect_ride(page, rid) for rid in ride_values]

        # If a ride is not in previously checked rides and status is available or full:
        # 1. Send a notification to users
        # 2. Book if available
        # 3. Add to wait list if full
        # 4. Add it to the previously checked list

        # If a ride is available or full and the user is not already on the ride, then notify the user

        # First filet the rides for all previously checked rides
        not_checked = [ride for ride in rides if ride["ride_id"] not in previously_checked_rides]
        LOGGER.info("Found %d rides that haven't been checked before.", len(not_checked))

        active_rides = [
            ride for ride in not_checked
            if ride["Ride status"] in [RideStates.AVAILABLE.value, RideStates.FULL.value]
        ]
        LOGGER.info("Found %d rides that are new and available or full.", len(active_rides))

        for ride in not_checked:
            if ride["Ride status"] in [RideStates.AVAILABLE.value, RideStates.FULL.value]:

                LOGGER.info(
                    "New ride found: rid=%s, date=%s, desc=%s", ride["ride_id"], ride["Date"], ride["Description"]
                )

                # Notify the user about all new rides
                notify_ride(ride)

                # Book if the ride is available and the user is not already on a ride
                if (
                    ride["Ride status"] == RideStates.AVAILABLE.value
                    and ride["Your status"] == "Not on ride"
                    and ride["Description"].startswith("Fri")  # Only auto-book FRI rides for now
                ):
                    LOGGER.info("Booking ride: %s, %s, %s", ride["ride_id"], ride['Date'], ride['Description'])
                    # book_ride(page, ride["ride_id"])
                    notify_booking_or_waitlist(ride, action="booked")

                # Waitlist if the ride is full and the user is not already on a ride
                if (
                    ride["Ride status"] == RideStates.FULL.value
                    and ride["Your status"] == "Not on ride"
                    and ride["Description"].startswith("Fri")  # Only auto-waitlist FRI rides for now
                ):
                    LOGGER.info("Waitlisting: %s, %s, %s", ride["ride_id"], ride["Date"], ride["Description"])
                    # add_to_wait_list(page, ride["ride_id"])
                    notify_booking_or_waitlist(ride, action="waitlisted")

            add_to_previously_checked_rides(ride["ride_id"])

        remove_old_rides_from_previously_checked_rides(
            filename=PREVIOUSLY_CHECKED_RIDES_FILE,
            valid_ride_ids=[ride["ride_id"] for ride in rides]
        )

        # Keeps the browser open so you can inspect it manually
        # LOGGER.info("Finished. Press Ctrl+C in terminal to close.")
        # page.pause()  # This opens the Playwright Inspector - great for debugging!


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    main()
