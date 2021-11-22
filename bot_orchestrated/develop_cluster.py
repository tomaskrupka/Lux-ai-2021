import copy
import math

import develop_cluster_actions as dca
import cluster_extensions as ce
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
    units_taken_action_ids = []  # Growing list of units that have taken action to prevent multiple commands.
    cannot_act_units = []  # Growing list of used units that cannot act this turn.

    cannot_act_units = ce.get_cannot_act_units(cluster)  # init with units with cooldown
    blocked_positions += cannot_act_units

    cities_by_fuel = ce.get_cities_fuel_balance(cluster, 10).values()

    # CITY TILE ACTIONS

    a, units_allowance, units_surplus, researched = dca.build_workers_or_research(
        cluster, cluster_development_settings)
    actions += a

    # BUILD CITY TILES
    # TODO: exclude units coming to the city with resources.

    a, b, uta = dca.build_city_tiles(cluster, units_taken_action_ids)
    actions += a
    blocked_positions += b
    units_taken_action_ids += uta

    # EXPORT UNITS FROM PUSH OUT POSITIONS

    push_out_positions: list  # ordered positions to export from without my units
    push_out_units: list  # ordered units next to export positions

    push_out_units, push_out_positions = ce.detect_push_out_units_positions(cluster, cluster_development_settings)
    to_push_out_count = min(units_surplus, cluster_development_settings.units_export_count)

    a, b, uta, satisfied_export_positions = dca.push_out_units_for_export(
        cluster,
        cluster_development_settings,
        to_push_out_count,
        blocked_positions,
        units_taken_action_ids,
        push_out_units)
    actions += a
    blocked_positions += b
    units_taken_action_ids += uta

    # PUSH OUT FROM CITIES

    to_push_out_count_remaining = to_push_out_count - len(uta)

    a, b, uta = dca.push_out_from_cities(
        cluster,
        blocked_positions,
        to_push_out_count - to_push_out_count_remaining,
        push_out_positions,
        units_taken_action_ids)

    actions += a
    blocked_positions += b
    units_taken_action_ids += uta

    # PULL UNITS BACK INTO CITIES

    if extensions.get_days_to_night(cluster_development_settings.turn) < 3:
        a, uta = dca.pull_units_to_cities(cluster, cannot_act_units, units_taken_action_ids)
        actions += a
        units_taken_action_ids += uta

    # STEP OUT OF RESOURCES INTO ADJACENT EMPTY POSITIONS

    forbidden_targets = [p for p, i in cluster.cell_infos.items() if i.my_units or p in blocked_positions]

    a, b, uta, unmoved_units_on_resource = dca.step_out_of_resources_into_adjacent_empty(
        cluster, cluster_development_settings, forbidden_targets, units_taken_action_ids)
    actions += a
    blocked_positions += b
    units_taken_action_ids += uta

    # STEP WITHIN RESOURCES IF STEP OUT WAS UNSUCCESSFUL

    if unmoved_units_on_resource:
        a, b, uta, units_on_resource = dca.step_within_resources(
            unmoved_units_on_resource,
            cluster,
            cluster_development_settings,
            blocked_positions)
        actions += a
        blocked_positions += b
        units_taken_action_ids += uta

        # IF UNIT ON RESOURCE COULD NOT MOVE, PULL IT BACK TO CITY

        a, b = dca.step_into_city(units_on_resource, cluster, cluster_development_settings, cities_by_fuel)
        actions += a
        blocked_positions += b

    # STEP OUT OF CITIES INTO MINING POSITIONS

    a = dca.step_out_of_cities_into_mining(
        cluster,
        cluster_development_settings,
        blocked_positions,
        units_taken_action_ids)
    actions += a
    actions_allowance = [actions, units_allowance, researched]
    return actions_allowance
