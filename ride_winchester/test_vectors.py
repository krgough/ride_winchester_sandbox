""" Test Vectors for Ride Winchester Appointment Scheduling Problem """

from datetime import datetime, timedelta
from pprint import pprint
import random


test_vectors = {
    "test1": {
        "rides": ['A1', 'A2', 'A3', 'A4', 'A5', 'A6'],
        "leader_offers": {
            'Leader_X': ['A1', 'A2', 'A3'],
            'Leader_Y': ['A1', 'A2', 'A4', 'A5'],
            'Leader_Z': ['A3', 'A4', 'A5']
        }
    },
    "test2": {
        "rides": ['9:00AM', '9:30AM', '10:00AM', '10:30AM', '11:00AM', '11:30AM'],
        "leader_offers": {
            'Alice': ['9:00AM', '9:30AM', '10:00AM'],
            'Bob':   ['9:30AM', '10:00AM', '10:30AM', '11:00AM'],
            'Charlie': ['10:00AM', '10:30AM', '11:00AM'],
            'David': ['9:00AM', '11:00AM']
        }
    }
}


def generate_test_data(num_rides=90, num_leaders=6, offers_low=0.05, offers_high=0.1):
    """ Generates test data for ride allocation
        offers_low = lowest number of offers per leader as a fraction of total rides
        offers_high = highest number of offers per leader as a fraction of total rides
        num_rides = total number of rides to generate
        num_leaders = total number of leaders to generate
    """

    # Define a time range for appointments (e.g. next 90 days at 09:30 each day)
    rides = []
    start_date = datetime.now().replace(hour=9, minute=30, second=0, microsecond=0)
    for day in range(num_rides):
        rides.append((start_date + timedelta(days=day)).strftime("%Y-%m-%d %H:%M"))

    # Shuffle to mix up the order, so the algorithm doesn't benefit from inherent sorting
    random.shuffle(rides)

    # Generate Leaders
    leaders = [f"Leader_{i+1}" for i in range(num_leaders)]

    # Generate leader offfers
    offers = {}
    for leader in leaders:

        # Assign a random "availability preference" (0.05 to 0.1 of all appointments)
        # This determines how many rides a leader is potentially available for
        num_offers = random.randint(
            int(offers_low * len(rides)),
            int(offers_high * len(rides))
        )

        # Randomly pick rides for which this leader is available
        offers[leader] = random.sample(
            population=rides,
            k=num_offers
        )

    return rides, offers


def test_generate_test_data():
    """ Test the generate_test_data function """
    num_rides = 90
    num_leaders = 6
    offers_low = 0.05
    offers_high = 0.1

    rides, offers = generate_test_data(
        num_rides=num_rides,
        num_leaders=num_leaders,
        offers_low=offers_low,
        offers_high=offers_high
    )
    pprint(rides)
    pprint(offers)
    assert len(rides) == num_rides
    assert len(offers) == num_leaders
    for _, rides in offers.items():
        assert int(offers_low * num_rides) <= len(rides) <= int(offers_high * num_rides)

    print("Test passed!")


if __name__ == "__main__":
    test_generate_test_data()
