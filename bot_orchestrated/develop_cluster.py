import copy
import math
import time

import develop_cluster_actions as dca
import cluster_extensions as ce
import extensions
from cluster import Cluster, ClusterDevelopmentSettings
from lux import annotate
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

    # HIGHLIGHT EXPORT SETTINGS

    for pos in cluster_development_settings.units_export_positions:
        actions.append(annotate.circle(pos.x, pos.y))

    # RECON BLOCKED POSITIONS

    b, c = ce.get_cannot_act_units(cluster)  # units with cooldown
    blocked_positions += b
    cannot_act_units_ids += c
    b = ce.get_opponent_city_tiles(cluster)
    blocked_positions += b

    # if game_state.turn == 70:
    #     print('my turn')

    # CITY TILE ACTIONS

    a, units_allowance, units_surplus, researched = dca.build_workers_or_research(
        cluster, cluster_development_settings, 2)
    actions += a

    # BUILD CITY TILES OR REFUEL CITIES FROM UNITS WITH NON-WOOD CARGO INSTEAD OF BUILDING
    # TODO: exclude units coming to the city with resources.

    a, b, c = dca.build_city_tiles(cluster, cannot_act_units_ids, cluster_development_settings)
    actions += a
    blocked_positions += b
    cannot_act_units_ids += c
    #
    # a, b, c = dca.build_city_tiles_or_refuel(cluster, cannot_act_units_ids, cluster_development_settings.turn)
    # actions += a
    # blocked_positions += b
    # cannot_act_units_ids += c

    # EXPORT UNITS FROM PUSH OUT POSITIONS

    push_out_positions: set  # positions to export from without my units
    push_out_units: set  # units next to export positions

    push_out_units, push_out_positions = ce.detect_push_out_units_positions_anywhere(cluster, cluster_development_settings)
    to_push_out_count = units_surplus

    if not night_mode:
        a, b, c, satisfied_export_positions, remains_to_push_out = dca.export_units(
            cluster,
            cluster_development_settings,
            to_push_out_count,
            blocked_positions,
            cannot_act_units_ids,
            push_out_units)
        actions += a
        blocked_positions += b
        cannot_act_units_ids += c

        # PUSH OUT

        a, b, c = dca.push_out_from_anywhere(
            cluster,
            blocked_positions,
            remains_to_push_out,
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

    # STEP OUT OF RESOURCES INTO CITIES WITH UNITS THAT HAVE FULL CARGO

    # a, c = dca.step_out_of_resources_into_cities_with_full_cargo_units(cluster, cannot_act_units_ids, cities_scores)
    # actions += a
    # cannot_act_units_ids += c

    # STEP WITHIN RESOURCES IF STEP OUT WAS UNSUCCESSFUL

    blocked_positions_now = ce.get_blocked_positions_now(cluster, blocked_positions, cannot_act_units_ids)

    if unmoved_units_on_resource:
        a, b, c, units_on_resource = dca.step_within_resources(
            unmoved_units_on_resource,
            cluster,
            cluster_development_settings,
            blocked_positions_now,
            cannot_act_units_ids)
        actions += a
        blocked_positions += b
        cannot_act_units_ids += c

        # IF SOME UNITS ON RESOURCES COULD NOT MOVE, PULL THEM BACK TO CITY

        # todo: this pulls units not only from cities, but also those from perimeter that should stay and mine. replace this and stepping within resources with properly directing units somewhere desirable.
        # if not night_mode:
        #     a, c = dca.pull_units_to_cities(cluster, cities_scores, cannot_act_units_ids)
        #     actions += a
        #     cannot_act_units_ids += c

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
        a, c = dca.step_within_cities_into_better_mining_positions(cities_mineabilities, cluster,
                                                                   cannot_act_units_ids)
        actions += a
        cannot_act_units_ids += c
    #
    # end = time.time()
    # elapsed = (end - start) * 1000
    # if elapsed > 1000:
    #     print(elapsed)

    # MOVE THROUGH UNRESEARCHED RESOURCE
    #
    # if cluster_development_settings.turn == 60:
    #     print('my turn')

    stuck_units_not_in_city = ce.get_stuck_units_not_in_city(cluster, cluster_development_settings.mined_resource)
    if stuck_units_not_in_city:
        blocked_positions_now = ce.get_blocked_positions_now(cluster, blocked_positions, cannot_act_units_ids)
        a, b, c, stuck_units_not_in_city = dca.step_within_resources(
            stuck_units_not_in_city,
            cluster,
            cluster_development_settings,
            blocked_positions_now,
            cannot_act_units_ids)
        actions += a
        blocked_positions += b
        cannot_act_units_ids += c


    # STEP OUT OF RESOURCE INTO ADJACENT MINING POSITION AT NIGHT IF MULTIPLE UNTIS ON POSITION

    stuck_units_ids = ce.get_stuck_units_in_city(cluster, cannot_act_units_ids)
    disallowed_units = ce.get_disallowed_units_for_night_move_out(cluster, cannot_act_units_ids, stuck_units_ids)

    if night_mode:
        a, b, c = dca.step_out_of_cities_into_mining(
            cluster,
            cluster_development_settings,
            blocked_positions,
            disallowed_units)
        actions += a
        cannot_act_units_ids += c

    # CHURN UNITS IN A CITY

    # if not night_mode:
    #     a, c = dca.churn_inside_city(cities_mineabilities, cluster, cannot_act_units_ids)
    #     actions += a
    #     cannot_act_units_ids += c

    # HANDLE IDLE UNITS:

    # UNITS TRAPPED WITH ACCESS TO NOTHING BUT OPPONENT CITY, EMPTY TILE, OWN CITY, UNRESEARCHED RESOURCE

    # TRAPPED INSIDE A FULLY DEVELOPED CITY

    # UNITS IN A CITY AT NIGHT THAT IS ABOUT TO DIE THE NEXT ROUND



    return [actions, units_allowance, researched]

