import copy
import math

import develop_cluster_actions as dca
import cluster_extensions
import extensions
from cluster import Cluster, ClusterDevelopmentSettings
from lux.game import Game
from lux.game_map import Position

# TODO: moved units out of each method. -> a, b, m, then input into the next one.

def develop_cluster(cluster: Cluster, cluster_development_settings: ClusterDevelopmentSettings, game_state: Game):
    actions = []  # To submit to the agent.
    units_allowance: int  # How many units can other clusters build.
    units_surplus: int  # Units needed in this cluster - units_export_count.
    researched: int  # Prevent researching past 200 here and in other clusters.
    blocked_positions = []  # Growing list of taken positions during development to prevent collisions.
    cannot_act_units = []  # Growing list of used units that cannot act this turn.

    cannot_act_units = cluster_extensions.get_cannot_act_units(cluster)  # init with units with cooldown
    blocked_positions += cannot_act_units

    cities_by_fuel = cluster_extensions.get_cities_fuel_balance(cluster, 10).values()

    # CITY TILE ACTIONS

    a, units_allowance, units_surplus, researched = dca.build_workers_or_research(
        cluster, cluster_development_settings)
    actions += a

    # PULL UNITS BACK INTO CITIES

    if extensions.get_days_to_night(cluster_development_settings.turn) < 3:
        a, moved_units = dca.pull_units_to_cities(cluster, cannot_act_units)
        actions += a
    else:
        moved_units = []

    # BUILD CITY TILES
    # TODO: exclude units coming to the city with resources.

    a, b = dca.build_city_tiles(cluster)
    actions += a
    blocked_positions += b

    # STEP OUT OF RESOURCES INTO ADJACENT EMPTY POSITIONS

    forbidden_targets = [p for p, i in cluster.cell_infos.items() if i.my_units or p in blocked_positions]

    a, b, c, unmoved_units_on_resource = dca.step_out_of_resources_into_adjacent_empty(
        cluster, cluster_development_settings, forbidden_targets, moved_units)
    actions += a
    blocked_positions += b
    cannot_act_units += c

    # STEP WITHIN RESOURCES IF STEP OUT WAS UNSUCCESSFUL

    if unmoved_units_on_resource:
        a, b, units_on_resource = dca.step_within_resources(
            unmoved_units_on_resource,
            cluster,
            cluster_development_settings,
            blocked_positions)
        actions += a
        blocked_positions += b

        # IF UNIT ON RESOURCE COULD NOT MOVE, PULL IT BACK TO CITY

        a, b = dca.step_into_city(units_on_resource, cluster, cluster_development_settings, cities_by_fuel)
        actions += a
        blocked_positions += b

    # EXPORT UNITS FROM PUSH OUT POSITIONS

    push_out_units, push_out_positions = cluster_extensions.detect_push_out_units_positions(cluster,
                                                                                            cluster_development_settings)

    a, b, push_out_units_remaining, satisfied_export_positions, p = dca.push_out_units_for_export(
        cluster,
        cluster_development_settings,
        units_surplus,
        blocked_positions,
        push_out_units)
    actions += a
    blocked_positions += b
    push_out_units = p

    # FIND MOVES FROM CITIES TO UNSATISFIED EXPORTS

    city_push_outs = dca.get_city_push_outs(cluster, cluster_development_settings,
                                            push_out_units_remaining, satisfied_export_positions,
                                            push_out_units, push_out_positions)

    # STEP OUT OF CITIES INTO MINING AND PUSH-OUT POSITIONS

    a = dca.step_out_of_cities(cluster, cluster_development_settings, city_push_outs,
                               blocked_positions)
    actions += a
    actions_allowance = [actions, units_allowance, researched]
    return actions_allowance
