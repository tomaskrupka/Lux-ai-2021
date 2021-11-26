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
    cannot_act_units_ids = []  # Growing list of units that have taken action to prevent multiple commands.
    night_mode = extensions.get_days_to_night(cluster_development_settings.turn) < 3
    cities: dict  # id = city
    cities_scores: dict  # id = city_score
    cities_mineabilities: dict  # id = (dict: pos = mining_potential)

    cities, cities_scores, cities_mineabilities = ce.get_cities_scores_mineability(cluster, cluster_development_settings.mined_resource)

    b, c = ce.get_cannot_act_units(cluster)  # init with units with cooldown
    blocked_positions += b
    cannot_act_units_ids += c

    # todo: put opponent cities into blocked positions

    # if game_state.turn == 70:
    #     print('turn is 70')

    # CITY TILE ACTIONS

    a, units_allowance, units_surplus, researched = dca.build_workers_or_research(
        cluster, cluster_development_settings)
    actions += a

    # BUILD CITY TILES
    # TODO: exclude units coming to the city with resources.

    a, b, c = dca.build_city_tiles(cluster, cannot_act_units_ids)
    actions += a
    blocked_positions += b
    cannot_act_units_ids += c

    # EXPORT UNITS FROM PUSH OUT POSITIONS

    push_out_positions: set  # positions to export from without my units
    push_out_units: set  # units next to export positions

    push_out_units, push_out_positions = ce.detect_push_out_units_positions_anywhere(cluster, cluster_development_settings)
    to_push_out_count = units_surplus

    if not night_mode:
        a, b, c, satisfied_export_positions = dca.export_units(cluster, cluster_development_settings, to_push_out_count,
                                                               blocked_positions, cannot_act_units_ids, push_out_units)
        actions += a
        blocked_positions += b
        cannot_act_units_ids += c

    # PUSH OUT

    if not night_mode:
        to_push_out_count_remaining = to_push_out_count - len(c)

        a, b, c = dca.push_out_from_anywhere(
            cluster,
            blocked_positions,
            to_push_out_count_remaining,
            push_out_positions,
            cannot_act_units_ids)

        actions += a
        blocked_positions += b
        cannot_act_units_ids += c

    # PULL UNITS BACK INTO CITIES

    if night_mode:
        a, c = dca.pull_units_to_cities(cluster, cities_scores, cannot_act_units_ids)
        actions += a
        cannot_act_units_ids += c

    # STEP OUT OF RESOURCES INTO ADJACENT EMPTY POSITIONS

    blocked_positions_now = ce.get_blocked_positions_now(cluster, blocked_positions, cannot_act_units_ids)

    a, b, c, unmoved_units_on_resource = dca.step_out_of_resources_into_adjacent_empty(
        cluster, cluster_development_settings.mined_resource, blocked_positions_now, cannot_act_units_ids)
    actions += a
    blocked_positions += b
    cannot_act_units_ids += c

    # STEP WITHIN RESOURCES IF STEP OUT WAS UNSUCCESSFUL

    if unmoved_units_on_resource:
        a, b, c, units_on_resource = dca.step_within_resources(
            unmoved_units_on_resource,
            cluster,
            cluster_development_settings,
            blocked_positions)
        actions += a
        blocked_positions += b
        cannot_act_units_ids += c

        # IF SOME UNITS ON RESOURCES COULD NOT MOVE, PULL THEM BACK TO CITY

        if not night_mode:
            a, c = dca.pull_units_to_cities(cluster, cities_scores, cannot_act_units_ids)
            actions += a
            cannot_act_units_ids += c

    # STEP OUT OF CITIES INTO MINING POSITIONS

    if not night_mode:
        a, b, c = dca.step_out_of_cities_into_mining(
            cluster,
            cluster_development_settings,
            blocked_positions,
            cannot_act_units_ids)
        actions += a
        cannot_act_units_ids += c

    # MOVE WITHIN CITIES INTO BETTER MINING POSITIONS

    if night_mode:
        a, c = dca.step_within_cities_into_better_mining_positions(cities_mineabilities, cluster, cannot_act_units_ids)
        actions += a
        cannot_act_units_ids += c

    actions_allowance = [actions, units_allowance, researched]
    return actions_allowance
