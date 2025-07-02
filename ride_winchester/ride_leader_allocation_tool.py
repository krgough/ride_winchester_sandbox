r"""

# Problem Statement:
Assign maximum number of rides to leaders based on their availability offers.
Level the allocations accross ride leaders.  We make the cost of each additional
ride incrementally larger, so the algorithm prefers to spread rides evenly across leaders.

Uses the max-flow-min-cost algorithm to find the optimal assignment.

# Directed Graphs

A Directed Graph is used to represent the problem.

The graph has nodes and edges(connections between nodes):

Nodes:
    - source
    - sink
    - rides
    - ride leader
    - Edges: Links between nodes with capacities and costs.

         Source
         / | \
        /  |  \
      R1  R2  R3   << Rides
       |  / \  |
       | /   \ |   << Edges representing offers from leaders to rides (with cost and capacity)
       |/     \|
      L1      L2   << Ride leaders
        \    /
         \  /
         Sink

We want to maximise the flow through the graph (max rides allocated) while minimizing the cost
by leveling ride allocations across ride leaders.

- The Source node connects to each ride node with capacity 1 (each ride can be allocated once).
- Each ride is represented as a node.
- Each RL is represented as a node
- RL Nodes connect upwards to ride nodes they offer, with capacity 1 (RLs can take each ride once only).
- RL Nodes connect downwards to a Sink node with capacity equal to the maximum number of rides the RL offers.

To handle allocation leving RL nodes are represented by a sub-network as follows:
- Each RL has an "in" node and an "out" node.
- Each RL has a set of slot nodes that represent the number of rides they can take.
- Each subnoslot node has an incremental cost associated with it, so that the algorithm prefers to fill the RLs evenly.

e.g. If L1 offers R1 but their first offer slot is full then they can offer slot 2 at a cost of 2.
If L2 also offers R1 but their first offer slot is empty then we can achieve a lower cost by assigning
that ride to L2,Slot1 instead of L1,Slot2.

                     L1_in
         ______________|___________________
        |              |                   |
 offer_slot1       offer_slot2       offer_slotN
 (capacity=1)      (capacity=1)      (capacity=1)
 (cost=1)          (cost=2)          (cost=N)
        |              |                   |
         ----------------------------------
                       |
                     L1_out
             (capacity=leader_capacity)
                       |
                     Sink

# Max-Flow-Min-Cost

1. Find the maximum flow through the graph (max number of rides filled). There may be multiple solutions.
2. Set the source/sink demands to the calculated maximum flow value.
3. Use the min-cost-flow algorithm to find a minimum cost solution that achieves the given demand i.e. maximum flow.

"""


import logging
from pprint import pprint

import networkx as nx

import test_vectors

LOGGER = logging.getLogger(__name__)


def populate_graph(rides, leaders_offers):
    """ Create and populate a graph with nodes and edges """
    graph = nx.DiGraph()
    source = "SOURCE"
    sink = "SINK"

    # Add source and sink nodes
    graph.add_node(source)
    graph.add_node(sink)

    # Add ride nodes and edges from Source
    # Each ride can be filled by at most one leader (capacity 1)
    # We don't use costs here (deal with that in the leveling step) (weight=0)
    # Only using demand for sink/source nodes (demand=0)
    for ride_id in rides:
        graph.add_node(ride_id, demand=0)
        graph.add_edge(source, ride_id, capacity=1, weight=0)

    # Add user nodes and parallel edges for leveling
    for leader, offers in leaders_offers.items():

        leader_offer_count = len(offers)

        leader_in_node = f"{leader}_in"
        leader_out_node = f"{leader}_out"
        graph.add_node(leader_in_node, demand=0)
        graph.add_node(leader_out_node, demand=0)

        # Create parallel paths for each ride leader capacity slot
        for i in range(leader_offer_count):
            slot_node = f"{leader}_slot_{i}"
            graph.add_node(slot_node, demand=0)

            # Edge from user_in to the specific slot node (no cost to enter the slot)
            graph.add_edge(leader_in_node, slot_node, capacity=1, weight=0)

            # Edge from the slot node to user_out (this is where the cost for this specific slot is applied)
            # Note the cost increases with 'i', so the first slot is cheapest
            graph.add_edge(slot_node, leader_out_node, capacity=1, weight=i)

        # Connect user_out_node to the sink.
        # This edge has capacity equal to the user's total max_capacity.
        graph.add_edge(leader_out_node, sink, capacity=leader_offer_count, weight=0)

    # Add edges from rides to user_in_nodes where offers exist
    for leader, offers in leaders_offers.items():
        leader_in_node = f"{leader}_in"

        for offer in offers:
            if offer in rides:
                graph.add_edge(offer, leader_in_node, capacity=1, weight=0)
            else:
                print(f"Warning: Appointment '{offer}' for leader '{leader}' not found in all_appointments list.")
    return graph, source, sink


def assign_ride_leaders(graph, source, sink):
    """
    Assign rides to leader offers using max-flow-min-cost

    - Find the maximum flow throught the graph (max appointments filled).
    - set the source/sink demands to the maximum flow value.
    - Use the min-cost-flow algorithm to find a minimum cost solution that achieves the given demand.

    Args:
        G (nx.DiGraph): The directed graph representing the ride assignment problem.
        source (str): The source node in the graph.
        sink (str): The sink node in the graph.

    Returns:
        tuple: A tuple containing:
            - int: The maximum flow value (number of filled rides).
            - dict: A dictionary representing the flow on each edge.
    """
    # Calculate maximum flow
    max_flow_value, flow_dict = nx.maximum_flow(graph, source, sink)

    # Set the source and sink demands to the maximum flow value
    graph.nodes[source]['demand'] = -max_flow_value
    graph.nodes[sink]['demand'] = max_flow_value

    # Calculate the minimum cost flow based on the maximum flow
    try:
        flow_dict = nx.min_cost_flow(graph)

    except nx.NetworkXUnfeasible:
        print("No feasible flow found for the specified demand. Adjusting demand or graph might be needed.")
        return 0, {}

    # Return the number of rides allocated and the flow dictionary (the allocations)
    return max_flow_value, flow_dict


def extract_allocations(flow_dict, rides, leader_offers):
    """ Extract ride allocations from the flow dictionary """
    allocations = {
        leader: []
        for leader in leader_offers.keys()
    }

    for ride in rides:
        if ride in flow_dict:
            for leader, flow in flow_dict[ride].items():
                if flow > 0:
                    allocations[leader.replace('_in', '')].append(ride)
    return allocations


def tests():
    """Example usage of the appointment scheduling solver"""

    print("\nRunning simple test case #1")
    rides = test_vectors.test_vectors['test1']['rides']
    leader_offers = test_vectors.test_vectors['test1']['leader_offers']
    expected_allocations = test_vectors.test_vectors['test1']['expected_allocations']
    graph, source, sink = populate_graph(rides, leader_offers)
    rides_filled, flow_dict = assign_ride_leaders(graph=graph, source=source, sink=sink)
    pprint(extract_allocations(flow_dict, rides, leader_offers))
    print(f"Number of filled rides: {rides_filled} out of {len(rides)}")
    assert extract_allocations(flow_dict, rides, leader_offers) == expected_allocations, "Test case #1 failed"

    print("\nRunning simple test case #2")
    rides = test_vectors.test_vectors['test2']['rides']
    leader_offers = test_vectors.test_vectors['test2']['leader_offers']
    expected_allocations = test_vectors.test_vectors['test2']['expected_allocations']
    graph, source, sink = populate_graph(rides, leader_offers)
    rides_filled, flow_dict = assign_ride_leaders(graph=graph, source=source, sink=sink)
    pprint(extract_allocations(flow_dict, rides, leader_offers))
    print(f"Number of filled rides: {rides_filled} out of {len(rides)}")
    assert extract_allocations(flow_dict, rides, leader_offers) == expected_allocations, "Test case #2 failed"

    print("\nRunning complex test case #1")
    rides, leader_offers = test_vectors.generate_test_data(
        num_rides=90,
        num_leaders=6,
        offers_low=0.05,
        offers_high=0.2
    )
    graph, source, sink = populate_graph(rides, leader_offers)
    rides_filled, flow_dict = assign_ride_leaders(graph=graph, source=source, sink=sink)
    pprint(extract_allocations(flow_dict, rides, leader_offers))
    print(f"Number of filled rides: {rides_filled} out of {len(rides)}")
    print()


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    tests()
