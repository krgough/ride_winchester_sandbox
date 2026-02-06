"""
Steves' existing algo works by calculating the number of combinations of
rides offered by leaders.

Each leader offers a set of rides and a max limit e.g. leader may offer 4 rides but with a limit of 2.

combinations = n!/r!(n-r!). Remember that 0! is 1 by definition.

Leaders are placed in a list that is sorted by number of combinations.
Rides are allocated to the leader with the least number of combinations first.
e.g. Leaders with 1 offer and 1 ride get allocated first.

Subsequent leaders get their rides allocated using the remaining rides.
Rides that are less than 7days apart are not allocated to the same leader.
Leaders are allocated a maximum of 3 rides.

"""

import logging
from itertools import combinations

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_combinations(offers, max_rides):
    """
    Show the combinations of rides offered by a leader.
    :param offers: List of rides offered by the leader.
    :param max_rides: Maximum number of rides that can be allocated to the leader.
    :return: List of combinations.
    """
    n = len(offers)
    if n < max_rides:
        return []
    return list(combinations(offers, max_rides))


def create_offers(num_offers):
    """ Create a list of offers based on the number of offers """
    return [f"offer{offer}" for offer in range(1, num_offers + 1)]


def show_combinations():
    """ Stuff """
    for offers_len in range(1, 11):
        offers = create_offers(offers_len)
        print(offers_len, end='')
        for max_rides in range(1, offers_len+1):
            print(f" {max_rides},{len(get_combinations(offers, max_rides))} ", end='')
        print()


show_combinations()

