"""
Linear programming solution to Ride Winchester ride leader scheduling
"""

import pulp

# Define the problem
prob = pulp.LpProblem("Ride_Leader_Assignment", pulp.LpMaximize)

# Define the decision variables
A_Mon = pulp.LpVariable('A_Mon', 0, 1, pulp.LpBinary)
A_Wed = pulp.LpVariable('A_Wed', 0, 1, pulp.LpBinary)
# B_Sat = pulp.LpVariable('B_Sat', 0, 1, pulp.LpBinary)
C_Wed = pulp.LpVariable('C_Wed', 0, 1, pulp.LpBinary)
C_Sat = pulp.LpVariable('C_Sat', 0, 1, pulp.LpBinary)

# Define the objective function
# prob += A_Mon + A_Wed + B_Sat + C_Wed + C_Sat, "Total Rides Led"
prob += A_Mon + A_Wed + C_Wed + C_Sat, "Total Rides Led"

# 4. Define the constraints

# Ride Slot Constraints
# Each slot must be allocated a maximum of once only (i.e. to a single leader or none)
prob += A_Mon <= 1, "Monday_Slot"
prob += A_Wed + C_Wed <= 1, "Wednesday_Slot"
# prob += B_Sat + C_Sat <= 1, "Saturday_Slot"
prob += C_Sat <= 1

# Leader Availability Constraints
prob += A_Mon + A_Wed <= 1, "Adam_Max_Rides"
# prob += B_Sat <= 1, "Betty_Max_Rides"
# This constraint essentially means Charlie can do both available slots if not otherwise constrained.
# We would need to add a constraint here for all combinations of offers from Charlie
# that are less that 7 days apart
# prob += C_Wed + C_Sat <= 2, "Charlie_Max_Rides"
prob += C_Sat <= 1

# Solve the problem
prob.solve()

# Print the results
print("Status:", pulp.LpStatus[prob.status])
print("Total Rides Led (Objective Value):", pulp.value(prob.objective))

print("\nAssignments:")
print(f"Adam on Monday: {A_Mon.varValue}")
print(f"Adam on Wednesday: {A_Wed.varValue}")
print(f"Betty on Saturday: {B_Sat.varValue}")
print(f"Charlie on Wednesday: {C_Wed.varValue}")
print(f"Charlie on Saturday: {C_Sat.varValue}")

# You can also see which constraints are binding (met exactly) or slack (have room)
# for c in prob.constraints:
#     print(f"Constraint {c.name}: {c.value()} (Slack: {c.slack})")