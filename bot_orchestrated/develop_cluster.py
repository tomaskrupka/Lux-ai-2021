import copy
import math

import develop_cluster_actions
import cluster_extensions
from cluster import Cluster, ClusterDevelopmentSettings
from lux.game import Game
from lux.game_map import Position


def develop_cluster(cluster: Cluster, cluster_development_settings: ClusterDevelopmentSettings, game_state: Game):
    actions = []  # To submit to the agent.
    units_allowance: int  # How many units can other clusters build.
    units_surplus: int  # Units needed in this cluster - units_export_count.
    researched: int  # Prevent researching past 200 here and in other clusters.
    cannot_act_units: list  # Units that need to cool down.
    blocked_positions = []  # Growing list of taken positions during development to prevent collisions.

    cannot_act_units = cluster_extensions.get_cannot_act_units(cluster)
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

    forbidden_positions = [p for p, i in cluster.cell_infos.items() if i.my_units or p in blocked_positions]

    a, b, unmoved_units_on_resource = develop_cluster_actions.step_out_of_resources_into_adjacent_empty(
        cluster, cluster_development_settings, forbidden_positions)
    actions += a
    blocked_positions += b

    # STEP WITHIN RESOURCES IF STEP OUT WAS UNSUCCESSFUL

    if unmoved_units_on_resource:
        a, b, units_on_resource = develop_cluster_actions.step_within_resources(unmoved_units_on_resource, cluster,
                                                                                cluster_development_settings,
                                                                                blocked_positions)
        actions += a
        blocked_positions += b
        blocked_positions += units_on_resource  # Todo step into city instead

    # EXPORT UNITS FROM PUSH OUT POSITIONS

    push_out_units, push_out_positions = cluster_extensions.detect_push_out_units_positions(cluster,
                                                                                            cluster_development_settings)

    a, b, push_out_units_remaining, satisfied_export_positions, p = develop_cluster_actions.push_out_units_for_export(
        cluster,
        cluster_development_settings,
        units_surplus,
        blocked_positions,
        push_out_units)
    actions += a
    blocked_positions += b
    push_out_units = p

    # FIND MOVES FROM CITIES TO UNSATISFIED EXPORTS

    city_push_outs = develop_cluster_actions.get_city_push_outs(cluster, cluster_development_settings,
                                                                push_out_units_remaining, satisfied_export_positions,
                                                                push_out_units, push_out_positions)

    # STEP OUT OF CITIES INTO MINING AND PUSH-OUT POSITIONS

    a = develop_cluster_actions.step_out_of_cities(cluster, cluster_development_settings, city_push_outs,
                                                   blocked_positions)
    actions += a
    actions_allowance = [actions, units_allowance, researched]
    return actions_allowance
