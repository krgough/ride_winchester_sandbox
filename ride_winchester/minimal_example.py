r"""Minimum Cost Flow Example using NetworkX


     a = Source
    / \
   b   c                  b_capacity=2, weight=3
    \ /                   c_capacity=1, weight=2
     d = Sink

Max flow through the graph is 3.  Costs ignored for max flow.

We can set a demand on the source and sink nodes, and find the minimum cost flow in the graph.
Demand on source of -1 and sink of 1 means we want to push 1 unit of flow from source to sink.
Edges can have capacities and weights.  Weights represent the cost per unit of flow on that edge.

Min cost for demand 1 = 2,  a > c > d
Min cost for demand 2 = 5,  a > b > d (cost=3), a > c > d (cost=2)

"""

import networkx as nx

# Create a directed graph
G = nx.DiGraph()
SOURCE = "a"
SINK = "d"


def set_demands(source_demand, sink_demand):
    """ Set the demands on the source and sink nodes """
    G.nodes[SOURCE]['demand'] = source_demand
    G.nodes[SINK]['demand'] = sink_demand


def setup_the_graph():
    """ Add nodes and edges with capacities and weights (costs) """
    G.add_edge(SOURCE, "b", capacity=2, weight=3)
    G.add_edge("b", SINK, capacity=2, weight=0)
    G.add_edge(SOURCE, "c", capacity=1, weight=2)
    G.add_edge("c", SINK, capacity=1, weight=0)


def print_graph_info():
    """ Print the graph information """
    print("Graph nodes and their attributes:")
    for node in G.nodes(data=True):
        print(node)

    print("\nGraph edges and their attributes:")
    for u, v, data in G.edges(data=True):
        print(f"{u} -> {v}: {data}")


def print_flow(flow_dict):
    """ Print the flow on each edge """
    print("\nFlow on each edge:")
    for u, neighbors in flow_dict.items():
        for v, flow in neighbors.items():
            print(f"Flow from {u} to {v}: {flow}, cost: {G[u][v]['weight'] * flow}")


def tests():
    """ Run some tests to check the graph setup """

    setup_the_graph()
    demand = 1
    set_demands(source_demand=-demand, sink_demand=demand)

    assert G.number_of_nodes() == 4, "Graph should have 4 nodes"
    assert G.number_of_edges() == 4, "Graph should have 4 edges"

    print_graph_info()

    # Find the maximum flow
    flow_value, flow_dict = nx.maximum_flow(G, SOURCE, SINK)
    assert flow_value == 3, "Maximum flow should be 3"
    print(f"\nMaximum flow value: {flow_value}")
    print_flow(flow_dict)

    # Find the minimum cost flow for the given demands
    flow_dict = nx.min_cost_flow(G)
    min_cost = nx.cost_of_flow(G, flow_dict)
    assert min_cost == 2, f"Minimum cost should be 2 for demand {demand}"
    print(f"\nMinimum cost for demand={demand}: {min_cost}")
    print_flow(flow_dict)

    # Now increase the demand to 2
    demand = 2
    set_demands(source_demand=-demand, sink_demand=demand)
    # Find the minimum cost flow for the given demands
    flow_dict = nx.min_cost_flow(G)
    min_cost = nx.cost_of_flow(G, flow_dict)
    assert min_cost == 5, f"Minimum cost should be 5 for demand {demand}"
    print(f"\nMinimum cost for demand={demand}: {min_cost}")
    print_flow(flow_dict)


if __name__ == "__main__":
    tests()
