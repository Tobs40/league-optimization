# This is a brief demonstration of what our program was like at the time, with
# the Google Maps API being replaced by openrouteservice (open-source and free).
# This code uses the commercial software Gurobi.
#
# Gurobi has an academic license. Despite this,
# we aim to use an open-source solver in the future
# Modification of the code for the purpose of using another solver than Gurobi
# or another source than openrouteservice should be trivial
# Keep in mind that we have used a more performant formulation than in the paper
# Other solvers might need multiple times longer to find an optimal solution


import openrouteservice
import gurobipy as gp
from gurobipy import GRB
from geopy.distance import geodesic
from random import randint


# Register a free account at https://openrouteservice.org/
# Insert your API_KEY here
# Alternatively use straight line distance, see the code further below
# Note that the budget of openrouteservice's public instance might not be sufficient.
# Use straight line distances or setup an openrouteservice instance locally
API_KEY = 'YOUR_API_KEY' 
client = openrouteservice.Client(key=API_KEY)


# Defining some functions for computing distances:

# Takes two pairs of (latitude, longitude) coordinates and computes car distance and
# duration by car for going from the first pair of coordinates to the second
def distance_duration_car(s, e):

    if s == e:
        return 0.0, 0.0

    # openrouteservice requires coordinates as longitude, latitude
    route = client.directions(coordinates=(s[::-1], e[::-1]), profile='driving-car', format='json')
    
    summary = route['routes'][0]['summary']

    dis = summary['distance']  # Distance in meters
    dur = summary['duration']  # Duration in seconds

    return dis, dur


# Distance traveled by car in meters
def distance_car(s, e):
    return distance_duration_car[0]


# Travel time by car in seconds
def duration_car(s, e):
    return duration_car[1]


# Straight line distance in meters
def distance_straight_line(s, e):
    return geodesic(s, e).meters


# Choose your metric
metric = distance_straight_line
METRICS = [distance_car, duration_car, distance_straight_line]
assert metric in METRICS


# Creates a matrix for testing
# Chooses n coordinates uniform at random from a rectangle within Germany
# Uses straight line distances by default
def example_matrix(n, metric=distance_straight_line):
    assert metric in METRICS

    coordinates = [(randint(48, 55), randint(6, 15)) for _ in range(n)]
    matrix = [[None for _ in range(n)] for _ in range(n)]

    # Distance to oneself is 0
    for i in range(n):
        for j in range(n):
            matrix[i][j] = 0 if i == j  else metric(coordinates[i], coordinates[j])

    return matrix


# This is a quadratic formulation. It is more efficient than the one in the paper.
# The reason is, that Gurobi has a special way of exploiting the structure of this formulation
#
# In the paper, we used a linear formulation which took Gurobi significantly to solve
# However, the results are the exact same of course.
#
# Takes a distance matrix where matrix[i][j] is the distance from team i to team j
# returns an optimal solution with num_groups groups of size [min_size, max_size] and
# the length traveled in this solution
def optimize_ab(matrix, num_groups, min_size, max_size):

    num_teams = len(matrix)

    m = gp.Model("model")

    g = gp.tupledict()  # g_i_j = 1 if and only if team i is in group j

    for i in range(num_teams):
        for j in range(num_teams):
            g[i, j] = m.addVar(vtype=GRB.BINARY, name=f'g_{i}_{j}')

    obj = 0

    for i in range(num_teams):
        for j in range(num_teams):
            if i >= j:
                continue
            su = 0
            for k in range(num_groups):
                su += g[i, k] * g[j, k]

            # Each team travels twice per game, to the game and back home, so four travels in total
            obj += (1-su) * (2 * matrix[i][j] + 2 * matrix[j][i])

    m.setObjective(obj, GRB.MAXIMIZE)  # Maximize the sum of the distances not traveled

    # Force each team to be in one group exactly
    for i in range(num_teams):
        su = 0
        for j in range(num_groups):
            su += g[i, j]
        m.addConstr(su == 1, name=f'exactly_one_group_{i}')

    # Force each group's size to be within the range [min_size, max_size]
    for j in range(num_groups):
        su = 0
        for i in range(num_teams):
            su += g[i, j]
        if min_size is not None:
            m.addConstr(su >= min_size, name=f'min_league_size')
        if max_size is not None:
            m.addConstr(su <= max_size, name=f'max_league_size')

    m.optimize()

    teams_to_groups = [None for _ in range(len(matrix))]

    for i in range(num_teams):
        for k in range(num_groups):
            if g[i, k].X > 0.5:  # if the binary variable is 1, accounting for numerical inaccuracies
                assert teams_to_groups[i] is None
                teams_to_groups[i] = k

    total_distance_traveled = 0  # Total distance traveled by all teams

    for i in range(num_teams):
        for j in range(i+1, num_teams):
            for k in range(num_groups):
                if g[i, k].X > 0.5 and g[j, k].X > 0.5:  # Team i and j are both in group k
                    total_distance_traveled += matrix[i][j] * 2 + matrix[j][i] * 2

    return teams_to_groups, total_distance_traveled


def main():
    num_teams = 100  # How many teams to random example should use
    num_groups = 5  # Into how many groups the teams should be divided
    min_size = 1  # Minimum number of teams in a group
    max_size = num_teams  # Maximum number of teams in a group

    print('Generating random example matrix for {} teams'.format(num_teams))
    matrix = example_matrix(num_teams)

    print('Computing optimal solution for {} teams, dividing into {} groups of sizes {} to {}'.format(num_teams, num_groups, min_size, max_size))
    teams_to_groups, total_distance_traveled = optimize_ab(matrix, num_groups, min_size, max_size)

    groups = [[] for _ in range(num_groups)]

    for i, group in enumerate(teams_to_groups):
        groups[group].append(i)

    for i, group in enumerate(groups):
        print('Group {}: '.format(i), end='')
        for team in group:
            print('{} '.format(team), end='')
        print('(size {})'.format(len(group)))

    print()

    print('Teams travel {} units in total'.format(total_distance_traveled))


if __name__ == '__main__':
    main()

