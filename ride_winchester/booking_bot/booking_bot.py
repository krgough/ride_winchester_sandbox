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
import platform
import sys
import time

import requests

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright

LOGGER = logging.getLogger(__name__)


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
    NOT_AVAILABLE = "Leader not set ride yet"
    NO_LEADER = "No Leader"
    FULL = "Ride full"
    UNKNOWN = "Unknown"


load_dotenv(Path(__file__).parent / ".env")  # Load environment variables from .env file

ENV_VARS = {
    "RW_URL": os.getenv("RW_URL", None),
    "USERNAME": os.getenv("RW_USERNAME", None),
    "PASSWORD": os.getenv("RW_PASSWORD", None),
    "NOTIFICATION_TOPIC": os.getenv("NOTIFICATION_TOPIC", None),
    # "NOTIFICATION_TEST_TOPIC": os.getenv("NOTIFICATION_TEST_TOPIC", None),
    "HEADLESS": os.getenv("HEADLESS", None),
    "FILTER_DAYS": os.getenv("FILTER_DAYS", None),
    "FILTER_PACES": os.getenv("FILTER_PACES", None)
}

if not all(ENV_VARS.values()):
    missing_vars = [key for key, value in ENV_VARS.items() if not value]
    LOGGER.error("The following environment variables are missing from the .env file: %s", ", ".join(missing_vars))
    sys.exit(1)

ENV_VARS["HEADLESS"] = ENV_VARS["HEADLESS"] == "True"

ENV_VARS["FILTER_DAYS"] = [
    Days[day.strip().upper()]
    for day in ENV_VARS["FILTER_DAYS"].split(",")
] if ENV_VARS["FILTER_DAYS"] else None

ENV_VARS["FILTER_PACES"] = [
    Paces[pace.strip().upper()]
    for pace in ENV_VARS["FILTER_PACES"].split(",")
] if ENV_VARS["FILTER_PACES"] else None

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

    return parser.parse_args()


def login(page, rw_url=ENV_VARS["RW_URL"]):
    """ Navigate to login page and perform login using credentials from .env file. """
    # Go to the login page and enter creds
    LOGGER.info("Navigating to login...")
    page.goto(rw_url)

    # Fill in the login creds
    page.fill('input[name="userid_email"]', ENV_VARS["USERNAME"])
    page.fill('input[name="pwd"]', ENV_VARS["PASSWORD"])

    # Click the login button and wait for the page to load
    page.get_by_role("button", name="Sign In").click()
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
        time.sleep(0.5)
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

    time.sleep(1)  # Wait a bit for the page to update after changing filters


def get_ride_status(page, field_name):
    """ Get the ride status from the ride details page.
    Returns the status text if found, otherwise returns the default value.

    Ride status
    """
    row = page.locator("table tr", has_text=f"{field_name}").first

    # Handle no matching row found
    if row.count() == 0:
        return None

    # handle rows with insufficient cells gracefully
    cells = row.locator("td")
    if cells.count() < 2:
        return None

    return cells.nth(1).inner_text().strip() or None


def get_ride_note(page):
    """ Get the text immediately above the first table on the page.
    Returns the text if found, otherwise returns None.
    """

    text_above_table = page.evaluate("""() => {
        const table = document.querySelector('table');
        if (!table) return null;

        const range = document.createRange();
        range.setStart(document.body, 0);
        range.setEndBefore(table);

        const lines = range.toString()
            .split(/\\r?\\n/)
            .map(line => line.replace(/\\s+/g, ' ').trim())
            .filter(Boolean);

        return lines.length ? lines[lines.length - 1] : null;
    }""")

    return text_above_table


def inspect_rides(page):
    """ Inspect a given ride by its ID.
    This function should navigate to the ride details page,
    scrape the necessary information, and return it.
    """

    # Form a list of dicts representing each ride option in the select dropdown
    select = page.locator("select").first
    ride_details = select.locator("option").evaluate_all(
        """opts => opts.map((o, idx) => ({
            idx,
            ride_id: o.value,
            label: (o.textContent || '').trim()
        }))"""
    )

    for ride in ride_details:
        select.select_option(index=ride['idx'])
        page.wait_for_load_state("networkidle")

        ride["Date"] = get_ride_status(page, "Date")
        ride["Description"] = get_ride_status(page, "Description")
        ride["Leader"] = get_ride_status(page, "Leader")
        ride["Distance"] = get_ride_status(page, "Distance")
        ride["Ride requires"] = get_ride_status(page, "Ride requires")
        ride["Max. num. on ride"] = get_ride_status(page, "Max. num. on ride")
        ride["Num. on ride"] = get_ride_status(page, "Num. on ride")
        ride["Num. waiting"] = get_ride_status(page, "Num. waiting")
        ride["Your status"] = get_ride_status(page, "Your status")

        status = get_ride_status(page, "Ride status")

        if not status:
            status = get_ride_note(page)

        # Map ride_status to RideStates if possible
        try:
            ride['status'] = RideStates(status)
        except ValueError:
            ride['status'] = RideStates.UNKNOWN
            LOGGER.warning("Ride ID %s, %s has unexpected status: %s", ride['ride_id'], ride['label'], status)

        LOGGER.debug("rideid %s:  %s, %s, %s", ride['ride_id'], ride["Date"], ride["Description"], ride["status"])

        page.go_back()

    return ride_details


def load_previously_checked_rides(filename):
    """ Load the list of previously checked rides """

    list_of_rides = []
    # Check if the file exists - if not create it
    if not os.path.exists(filename):
        LOGGER.info("Previously checked rides file not found. Using empty list.")
    else:
        with open(filename, "r", encoding="utf-8") as f:
            list_of_rides = [line.strip() for line in f.readlines()]
    return list_of_rides


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
    page.goto(f"{ENV_VARS['RW_URL']}ridedetails.php?ride={ride_id}")
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
        "Notifying user: New ride found! Ride Data: %s, %s, %s", ride['ride_id'], ride['Date'], ride['Description']
    )
    url = f"https://ntfy.sh/{ENV_VARS['NOTIFICATION_TOPIC']}"
    rw_url = f"{ENV_VARS['RW_URL']}/index.php?ride={ride['ride_id']}"
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
    title = f"Successfully {action} ride: {ride['DATE']}, {ride['DESCRIPTION']}"
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

    # Load the list of previously checked rides to avoid duplicate notifications
    previously_checked_rides = load_previously_checked_rides(filename=PREVIOUSLY_CHECKED_RIDES_FILE)

    with sync_playwright() as p:
        # Launch browser (headless=False so you can see the login happen)
        # Choose executable path based on platform
        launch_kwargs = {"headless": ENV_VARS["HEADLESS"]}
        if platform.system() == "Linux":
            # Raspberry Pi and other Linux systems use system-installed chromium
            launch_kwargs["executable_path"] = "/usr/bin/chromium-browser"
        
        browser = p.chromium.launch(**launch_kwargs)
        context = browser.new_context()
        page = context.new_page()

        # Go to the login page and enter creds
        login(page)

        # Goto the set filters page
        page.get_by_role("link", name="Filter", exact=True).click()
        # Set the day and pace filters
        set_ride_filters(page, ENV_VARS["FILTER_DAYS"], ENV_VARS["FILTER_PACES"])
        # Goto the list of rides page
        page.get_by_role("link", name="List View", exact=True).click()

        # Scrape the list of all Ride IDs and get the details for each ride
        ride_values = page.eval_on_selector_all("select#xx option", "options => options.map(o => o.value)")
        LOGGER.info("Found %d rides.", len(ride_values))
        rides = inspect_rides(page)

        # If a ride is not in previously checked rides and status is available or full:
        # 1. Send a notification to users
        # 2. Book if available
        # 3. Add to wait list if full
        # 4. Add it to the previously checked list

        # If a ride is available or full and the user is not already on the ride, then notify the user

        # First filter the rides for all previously checked rides
        not_checked = [ride for ride in rides if ride["ride_id"] not in previously_checked_rides]
        LOGGER.info("Found %d rides that haven't been checked before.", len(not_checked))

        # Then filter for rides that are available or full
        active_rides = [
            ride for ride in not_checked
            if ride["status"] in [RideStates.AVAILABLE, RideStates.FULL]
        ]
        LOGGER.info("Found %d rides that are new and available or full.", len(active_rides))

        for ride in active_rides:

            LOGGER.info(
                "New active ride found: rid=%s, date=%s, desc=%s", ride["ride_id"], ride["Date"], ride["Description"]
            )

            # Notify the user about all new rides
            notify_ride(ride)

            # # Book if the ride is available and the user is not already on a ride
            # if (
            #     ride["RIDE STATUS"] == RideStates.AVAILABLE.value
            #     and ride["YOUR STATUS"] == "Not on ride"
            #     and ride["DESCRIPTION"].startswith("Fri")  # Only auto-book FRI rides for now
            # ):
            #     LOGGER.info("New AVAILABLE ride: %s, %s, %s", ride["RIDE_ID"], ride["DATE"], ride["DESCRIPTION"])
            #     # book_ride(page, ride["ride_id"])
            #     notify_booking_or_waitlist(ride, action="booked")

            # # Waitlist if the ride is full and the user is not already on a ride
            # # TODO: Only autobooking friday rides for now.
            # elif (
            #     ride["RIDE STATUS"] == RideStates.FULL.value
            #     and ride["YOUR STATUS"] == "Not on ride"
            #     and ride["DESCRIPTION"].startswith("Fri")  # Only auto-waitlist FRI rides for now
            # ):
            #     LOGGER.info("New FULL ride: %s, %s, %s", ride["RIDE_ID"], ride["DATE"], ride["DESCRIPTION"])
            #     # add_to_wait_list(page, ride["RIDE_ID"])
            #     notify_booking_or_waitlist(ride, action="waitlised")

            # Now we have checked this ride we mark is so that we don't try to book/waitlist/notify again
            add_to_previously_checked_rides(ride["ride_id"])

        remove_old_rides_from_previously_checked_rides(
            filename=PREVIOUSLY_CHECKED_RIDES_FILE,
            valid_ride_ids=[ride["ride_id"] for ride in rides]
        )

        # Keeps the browser open so you can inspect it manually
        # LOGGER.info("Finished. Press Ctrl+C in terminal to close.")
        # page.pause()  # This opens the Playwright Inspector - great for debugging!


if __name__ == "__main__":
    logging.basicConfig(level=logging.DEBUG)
    logging.getLogger("asyncio").setLevel(logging.WARNING)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    main()
