import math

import develop_cluster_actions
import extensions
from churn import solve_churn_with_score, get_move_actions_with_blocks
from cluster_extensions import can_mine_on_position, get_adjacent_mining_positions, get_mined_resource, \
    get_adjacent_positions_within_cluster, detect_push_out_units_positions
from cluster import Cluster, ClusterDevelopmentSettings
from lux.game_map import Position


def develop_cluster(cluster: Cluster, cluster_development_settings: ClusterDevelopmentSettings):
    actions = []  # To submit to the agent.
    units_allowance: int  # How many units can other clusters build.
    units_surplus: int  # Units needed in this cluster - units_export_count.
    researched: int  # Prevent researching past 200 here and in other clusters.
    cannot_act_units: list  # Units that need to cool down.
    blocked_positions = []  # Where my units cannot move. Dynamically update as moves happen.

    cannot_act_units = develop_cluster_actions.get_cannot_act_units(cluster)
    blocked_positions += cannot_act_units

    # CITY TILE ACTIONS

    a, units_allowance, units_surplus, researched = develop_cluster_actions.build_workers_or_research(
        cluster, cluster_development_settings)
    actions += a

    # BUILD CITY TILES
    # TODO: exclude units coming to the city with resources.

    a, b = develop_cluster_actions.build_city_tiles(cluster)
    actions += a
    blocked_positions += b

    # STEP OUT OF RESOURCES INTO ADJACENT EMPTY POSITIONS

    a, b, units_on_resource, empty_development_positions = develop_cluster_actions.step_out_of_resources_into_adjacent_empty(
        cluster, cluster_development_settings, cannot_act_units, blocked_positions)
    actions += a
    # FIXME: the step_out_of_resources_into_adjacent does not free blocked positions.
    blocked_positions += b

    # STEP WITHIN RESOURCES IF STEP OUT WAS UNSUCCESSFUL

    if units_on_resource:
        a, units_on_resource = develop_cluster_actions.step_within_resources(
            units_on_resource, cluster, cluster_development_settings, empty_development_positions, cannot_act_units)
        actions += a

    # EXPORT UNITS FROM PUSH OUT POSITIONS

    push_out_units, push_out_positions = detect_push_out_units_positions(cluster, cluster_development_settings)

    # FIXME: this does not add new blocked positions, just remove old ones
    a, b, push_out_units_remaining, satisfied_export_positions, p = develop_cluster_actions.push_out_units_for_export(
        cluster,
        cluster_development_settings,
        units_surplus,
        blocked_positions,
        push_out_units)
    actions += a
    blocked_positions = b
    push_out_units = p

    # FIND MOVES FROM CITIES TO UNSATISFIED EXPORTS

    city_push_outs = develop_cluster_actions.get_city_push_outs(cluster, cluster_development_settings, push_out_units_remaining, satisfied_export_positions, push_out_units, push_out_positions)

    # STEP OUT OF CITIES INTO MINING AND PUSH-OUT POSITIONS

    a = develop_cluster_actions.step_out_of_cities(cluster, cluster_development_settings, city_push_outs, cannot_act_units, units_on_resource, blocked_positions)
    actions += a
    actions_allowance = [actions, units_allowance, researched]
    return actions_allowance


# Steps within resources towards empty development positions.

def solve_churn(positions_options):
    move_solutions = dict()
    churn = dict()
    for position, options in positions_options:
        for option in options:
            churn[option] = churn[option] + 1 if option in churn else 1
    # units with least options first
    positions_options.sort(key=lambda x: (len(x[1])))
    move_demands = list(churn.items())
    # least demanded positions first
    move_demands.sort(key=lambda x: (x[1]))
    blocked_moves = set()
    for position_options in positions_options:
        unit_pos = position_options[0]
        unit_options = position_options[1]
        unit_moved = False
        for demand_option in move_demands:
            move_pos = demand_option[0]
            if move_pos in unit_options and move_pos not in blocked_moves:
                blocked_moves.add(move_pos)
                if unit_pos in move_solutions:
                    move_solutions[unit_pos].append(move_pos)
                else:
                    move_solutions[unit_pos] = [move_pos]
                unit_moved = True
                break
        if not unit_moved:
            if unit_pos in move_solutions:
                move_solutions[unit_pos].append(None)
            else:
                move_solutions[unit_pos] = [None]
    return move_solutions


def get_move_actions(moves_solutions, cluster):
    blocked_positions = []
    actions = []
    for pos, solutions in moves_solutions.items():
        for target, unit in zip(solutions, cluster.cell_infos[pos].my_units):
            if target is None:
                blocked_positions.append(pos)
            else:
                direction = extensions.get_directions_to_target(pos, target)
                actions.append(unit.move(direction))
    return actions, blocked_positions


def get_closest_development_position(cluster: Cluster, xy):
    min_dist = math.inf
    closest_position = None
    for (x, y) in cluster.development_positions:
        dist = abs(x - xy[0]) + abs(y - xy[1])
        if dist < min_dist:
            closest_position = (x, y)
            min_dist = dist
    return closest_position
