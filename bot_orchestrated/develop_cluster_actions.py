import math

import cluster_extensions
import extensions
from cluster import Cluster, CellInfo
from churn import solve_churn_with_score, get_move_actions_with_blocks
from lux.game_map import Position
from lux.game_objects import Unit, City


def build_workers_or_research(cluster, cluster_development_settings, units_to_push_out):
    units_allowance = cluster_development_settings.units_build_allowance
    researched = 0  # Prevent researching past 200 here and in other clusters
    units_needed, has_units = cluster_extensions.get_units_needed_for_maintenance(cluster)
    units_surplus = has_units - units_needed
    units_to_build = units_needed - has_units + units_to_push_out
    a = []
    for city_cell in [cell_info for cell_coords, cell_info in cluster.cell_infos.items() if cell_info.my_city_tile]:
        if city_cell.my_city_tile.can_act():
            if units_allowance > 0 and units_to_build > 0:
                a.append(city_cell.my_city_tile.build_worker())
                units_allowance -= 1
                units_to_build -= 1
                units_surplus += 1
            elif cluster_development_settings.research_level + researched < 200:
                a.append(city_cell.my_city_tile.research())
                researched += 1
    return a, units_allowance, units_surplus, researched


def pull_units_from_positions_to_cities(positions_infos, cluster: Cluster, cities_scores, cannot_act_units_ids):
    a = []
    c = []
    for cell_pos, cell_info in positions_infos:
        unit = cell_info.my_units[0]
        if unit.id in cannot_act_units_ids:
            continue
        options = cluster_extensions.get_adjacent_city_tiles_positions(cluster, cell_pos)
        if len(options) == 0:
            continue
        if len(options) == 1:
            direction = extensions.get_directions_to_target(cell_pos, options[0])
        else:
            high_score = -math.inf
            high_score_pos = None
            for option in options:
                city_id = cluster.cell_infos[option].my_city.cityid
                city_score = cities_scores[city_id]
                if city_score > high_score:
                    high_score_pos = option
                    high_score = city_score
            direction = extensions.get_directions_to_target(cell_pos, high_score_pos)
        a.append(unit.move(direction))
        c.append(unit.id)
    return a, c


def pull_units_to_cities(cluster: Cluster, cities_scores, cannot_act_units_ids):
    positions_infos = []
    for cell_pos, cell_info in cluster.cell_infos.items():
        if cell_info.my_units and not cell_info.my_city_tile:
            positions_infos.append((cell_pos, cell_info))
    a, c = pull_units_from_positions_to_cities(positions_infos, cluster, cities_scores, cannot_act_units_ids)
    return a, c


def step_within_cities_into_better_mining_positions(
        cities_mineabilities,
        cluster: Cluster,
        cannot_act_units_ids):
    a = []
    c = []
    for city_id in cities_mineabilities:
        top_positions = list(cities_mineabilities[city_id].items())
        top_positions.sort(key=lambda x: x[1], reverse=True)

        units_in_city_count = 0
        positions_units = dict()
        for pos in cities_mineabilities[city_id]:
            units = cluster.cell_infos[pos].my_units
            if units:
                units_in_city_count += len(units)
                positions_units[pos] = units

        do_not_use_units_ids = []
        for mining_pos, mineability in top_positions:
            if units_in_city_count == len(do_not_use_units_ids):
                break

            # If there is an unused unit, use it and continue to next mining pos.
            units = cluster.cell_infos[mining_pos].my_units
            if units:
                free_unit = next((u for u in units if u.id not in do_not_use_units_ids), None)
                if free_unit is not None:
                    do_not_use_units_ids.append(free_unit.id)
                    continue
            else:
                # Find closest free unit to pull
                for unit_pos, units in positions_units.items():
                    mining_pos_served = False
                    for unit in units:
                        if unit.id not in cannot_act_units_ids and unit.id not in do_not_use_units_ids:
                            all_directions = extensions.get_all_directions_to_target(unit_pos, mining_pos)
                            for direction in all_directions:
                                new_pos = extensions.get_new_position(unit_pos, direction)
                                if new_pos in cities_mineabilities[city_id]:
                                    a.append(unit.move(direction))
                                    c.append(unit.id)
                                    do_not_use_units_ids.append(unit.id)
                                    mining_pos_served = True
                                    break
                        if mining_pos_served:
                            break
                    if mining_pos_served:
                        break
    return a, c


def build_city_tiles(cluster, units_taken_actions_ids, cluster_development_settings):
    a = []
    b = []
    c = []
    for cell_pos, cell_info in cluster.cell_infos.items():
        if cell_info.is_empty and cell_info.my_units:
            unit = cell_info.my_units[0]
            if unit.can_act() and unit.get_cargo_space_left() == 0 and unit.id not in units_taken_actions_ids:
                can_build = True
                if extensions.get_days_to_night(cluster_development_settings.turn) < 2:
                    can_build = False
                    adjacent_positions = cluster_extensions.get_adjacent_positions_within_cluster(cell_pos, cluster)
                    adjacent_resources = 0
                    for adj_pos in adjacent_positions:
                        cell_info = cluster.cell_infos[adj_pos]
                        if cell_info.resource:
                            if cell_info.resource.type == 'wood':
                                adjacent_resources += 1
                            else:
                                adjacent_resources += 2
                        if cluster.cell_infos[adj_pos].my_city_tile or cluster.cell_infos[adj_pos].my_units:
                            can_build = True
                            break
                    if adjacent_resources >= 2:
                        can_build = True
                if can_build:
                    a.append(unit.build_city())
                    b.append(cell_pos)
                    c.append(unit.id)
    return a, b, c


# TODO : look past two.
def build_city_tiles_or_refuel(cluster, cannot_act_units_ids, turn):
    a = []
    b = []
    c = []
    for cell_pos, cell_info in cluster.cell_infos.items():
        if cell_info.is_empty and cell_info.my_units:
            unit = cell_info.my_units[0]
            if unit.can_act() and unit.get_cargo_space_left() == 0 and unit.id not in cannot_act_units_ids:
                refuel_pos = None
                # rule: do not build with coal or uranium if adjacent city needs refuel.
                if unit.cargo.coal > 0 or unit.cargo.uranium > 0:
                    adjacent_city_positions = cluster_extensions.get_adjacent_city_tiles_positions(cluster, cell_pos)
                    if adjacent_city_positions:
                        biggest_city_size = 0
                        for adj_pos in adjacent_city_positions:
                            city = cluster.cell_infos[adj_pos].my_city
                            can_survive = extensions.get_fuel_remaining_to_survival(city, turn) < 0
                            if not can_survive:
                                size = len(city.citytiles)
                                if size > biggest_city_size:
                                    biggest_city_size = size
                                    refuel_pos = adj_pos
                if refuel_pos is not None:  # no adjacent city or the city will survive
                    direction = extensions.get_directions_to_target(cell_pos, refuel_pos)
                    a.append(unit.move(direction))
                    c.append(unit.id)
                else:
                    a.append(unit.build_city())
                    b.append(cell_pos)
                    c.append(unit.id)
    return a, b, c


def step_out_of_resources_into_adjacent_empty(
        cluster,
        mined_resource,
        forbidden_targets,
        cannot_act_units_ids):
    positions_options = []
    unmoved_units_on_resource = []
    can_act_units_on_resource = []
    a = []
    b = []

    for cell_pos, cell_info in cluster.cell_infos.items():
        if cell_info.resource and cell_info.my_units:
            unit = cell_info.my_units[0]
            if unit.id not in cannot_act_units_ids:
                if unit.cargo.wood > 0 or unit.cargo.coal > 79 or unit.cargo.uranium > 93:
                    can_act_units_on_resource.append(cell_pos)
    for pos in can_act_units_on_resource:
        adjacent_development_positions = cluster_extensions.get_adjacent_development_positions(cluster, pos)
        # If unit at full capacity, let it move towards any resource
        considered_resource = mined_resource if cluster.cell_infos[pos].my_units[
                                                    0].get_cargo_space_left() > 0 else 'URANIUM'
        adjacent_mining_positions = cluster_extensions.get_adjacent_mining_positions(cluster, pos, considered_resource)
        if len(adjacent_development_positions) > 0:
            positions_options.append([pos, [p for p in adjacent_development_positions if
                                            p not in forbidden_targets and
                                            p in adjacent_mining_positions]])
        else:
            # had no adjacent development position
            unmoved_units_on_resource.append(pos)

    positions_scores = dict()
    for position, options in positions_options:
        for option in options:
            cell_info: CellInfo
            cell_info = cluster.cell_infos[option]
            positions_scores[option] = cluster_extensions.get_mining_potential_aggregate(cell_info.mining_potential, mined_resource)
    moves_solutions, scores = solve_churn_with_score(positions_options, positions_scores)
    moves, source_to_list, c = get_move_actions_with_blocks(positions_options, moves_solutions, cluster, [])
    a += moves

    for source, towards in source_to_list:
        if source == towards:
            unmoved_units_on_resource.append(towards)
        # elif cluster.cell_infos[towards].resource:  # Step may have happened outside
        else:
            b.append(towards)
            # c.append(source)

    return a, b, c, unmoved_units_on_resource


def step_within_resources(units_on_resource, cluster, cluster_development_settings, blocked_positions, cannot_act_units_ids):
    a = []
    b = []
    c = []

    # Hack: hide positions without resource from empty_development_positions to prevent trapping units
    # inside U-shaped cities. Remove this and score using real distance to empty development position (dijkstra)
    mineable_development_positions = [p for p in cluster.development_positions if
                                      sum(cluster.cell_infos[p].mining_potential.values()) > 0]

    if mineable_development_positions:
        # First try to move the units that are fully loaded. These can build next to locked resources. Then move the rest.
        for cycle_loaded in [True, False]:
            positions_scores = dict()
            for target in cluster.cell_infos:
                min_dist_to_export = 100
                for export_pos in cluster_development_settings.units_export_positions:
                    export_pos: Position
                    dist = export_pos.distance_to(target)
                    if min_dist_to_export > dist:
                        min_dist_to_export = dist
                min_dist_to_empty = 100
                for position in mineable_development_positions:
                    # Add position next to unlocked resources only for loaded units
                    can_mine_on_position = cluster_extensions.can_mine_on_position(
                        cluster,
                        position,
                        cluster_development_settings.mined_resource)
                    if cycle_loaded or can_mine_on_position:
                        dist = position.distance_to(target)
                        if dist < min_dist_to_empty:
                            min_dist_to_empty = dist
                positions_scores[target] = 10000 - min_dist_to_export * 1000 - min_dist_to_empty - 100 * (
                        cluster.cell_infos[target].my_city_tile is not None)

            positions_options = []
            for position in units_on_resource:
                unit = cluster.cell_infos[position].my_units[0]
                if unit.id not in cannot_act_units_ids:
                    is_loaded_unit = cluster.cell_infos[position].my_units[0].get_cargo_space_left() == 0
                    if cycle_loaded != is_loaded_unit:
                        continue
                    options = []
                    for adj_pos in cluster_extensions.get_adjacent_positions_within_cluster(position, cluster):
                        adj_cell_info = cluster.cell_infos[adj_pos]
                        if adj_cell_info.resource and adj_pos not in blocked_positions and adj_pos not in b:
                            options.append(adj_pos)
                    if len(options) > 0:
                        positions_options.append([position, options])

            moves_solutions, scores = solve_churn_with_score(positions_options, positions_scores)
            moves, source_to_list, cannot_act_ids = get_move_actions_with_blocks(positions_options, moves_solutions,
                                                                                 cluster, [])
            a += moves
            c += cannot_act_ids
            for source, towards in source_to_list:
                if towards != source:
                    b.append(towards)
                    units_on_resource.remove(source)

    return a, b, c, units_on_resource


def export_units(cluster,
                 cluster_development_settings,
                 units_to_push_out,
                 blocked_positions,
                 cannot_act_units_ids,
                 push_out_units):
    a = []
    b = []
    c = []
    satisfied_export_positions = []
    remains_to_push_out = units_to_push_out

    pushed_out_units_positions = []
    # For each export pos try to export any push-out unit
    for export_pos in cluster_development_settings.units_export_positions:
        if remains_to_push_out <= 0:
            break
        if export_pos in blocked_positions:
            continue
        for unit_pos in push_out_units:
            if unit_pos.is_adjacent(export_pos) and unit_pos not in pushed_out_units_positions:
                unit = cluster.cell_infos[unit_pos].my_units[0]
                if unit.id not in cannot_act_units_ids:
                    direction = extensions.get_directions_to_target(unit_pos, export_pos)
                    a.append(unit.move(direction))
                    b.append(export_pos)
                    c.append(unit.id)
                    pushed_out_units_positions.append(unit_pos)
                    satisfied_export_positions.append(export_pos)

                # Count as pushed even if could not act. Otherwise another unit would be pushed out of city to fulfill this.
                remains_to_push_out -= 1
                break

    return a, b, c, satisfied_export_positions, remains_to_push_out


def push_out_from_anywhere(
        cluster,
        blocked_positions,
        count_to_push_out,
        push_out_positions,
        cannot_act_units):
    a = []
    b = []
    c = []
    for push_pos in push_out_positions:
        if count_to_push_out <= 0:
            break
        if push_pos in blocked_positions:
            continue
        adjacent_positions = cluster_extensions.get_adjacent_positions_within_cluster(push_pos, cluster)
        unit_pushed = False
        for adj_pos in adjacent_positions:
            if cluster.cell_infos[adj_pos].my_units:
                for unit in cluster.cell_infos[adj_pos].my_units:
                    if unit.id not in cannot_act_units and unit.id not in c:  # unit can be visited multiple times as adjacent to different push out positions.
                        direction = extensions.get_directions_to_target(adj_pos, push_pos)
                        a.append(unit.move(direction))
                        b.append(push_pos)
                        c.append(unit.id)
                        count_to_push_out -= 1
                        unit_pushed = True
                        break
                if unit_pushed:
                    break
    return a, b, c


def push_out_from_cities(
        cluster,
        blocked_positions,
        count_to_push_out,
        push_out_positions,
        units_taken_actions_ids):
    a = []
    b = []
    c = []

    for push_pos in push_out_positions:
        if count_to_push_out <= 0:
            break
        if push_pos in blocked_positions:
            continue
        adjacent_positions = cluster_extensions.get_adjacent_positions_within_cluster(push_pos, cluster)
        unit_pushed = False
        for adj_pos in adjacent_positions:
            if cluster.cell_infos[adj_pos].my_city_tile and cluster.cell_infos[adj_pos].my_units:
                for unit in cluster.cell_infos[adj_pos].my_units:
                    if unit.can_act() and unit.id not in units_taken_actions_ids and unit.id not in c:  # unit can be visited multiple times as adjacent to different push out positions.
                        direction = extensions.get_directions_to_target(adj_pos, push_pos)
                        a.append(unit.move(direction))
                        b.append(push_pos)
                        c.append(unit.id)
                        count_to_push_out -= 1
                        unit_pushed = True
                        break
                if unit_pushed:
                    break

    return a, b, c


def step_out_of_resources_into_cities_with_full_cargo_units(cluster: Cluster, cannot_act_units_ids, cities_scores):
    positions_infos = []
    for cell_pos, cell_info in cluster.cell_infos.items():
        if cell_info.my_units:
            unit = cell_info.my_units[0]
            if unit.get_cargo_space_left() == 0:
                positions_infos.append((cell_pos, cell_info))
    a, c = pull_units_from_positions_to_cities(positions_infos, cluster, cities_scores, cannot_act_units_ids)
    return a, c


def step_out_of_cities_into_mining(cluster, cluster_development_settings, blocked_positions, cannot_act_units_ids):
    positions_options = []

    blocked_positions_now = cluster_extensions.get_blocked_positions_now(cluster, blocked_positions, cannot_act_units_ids)

    for cell_pos, cell_info in cluster.cell_infos.items():
        if cell_info.my_city_tile and cell_info.my_units:
            # free adjacent mining positions
            cell_pos_options = [p for p in
                                cluster_extensions.get_adjacent_mining_positions(
                                    cluster,
                                    cell_pos,
                                    cluster_development_settings.mined_resource) if
                                not cluster.cell_infos[p].my_city_tile and
                                not cluster.cell_infos[p].opponent_city_tile and
                                p not in blocked_positions_now]
            if len(cell_pos_options) > 0:
                for unit in cell_info.my_units:
                    if unit.id not in cannot_act_units_ids:
                        positions_options.append([cell_pos, cell_pos_options])
    positions_scores = dict()
    for position, options in positions_options:
        for option in options:
            positions_scores[option] = cluster_extensions.get_mining_potential_aggregate(
                cluster.cell_infos[option].mining_potential, cluster_development_settings.mined_resource)
    moves_solutions, scores = solve_churn_with_score(positions_options, positions_scores)
    a, source_to_list, c = get_move_actions_with_blocks(positions_options, moves_solutions, cluster, cannot_act_units_ids)
    b = []
    for source, towards in source_to_list:
        if towards != source:
            b.append(towards)
    return a, b, c

#
# # TODO: step into city that benefits the most from this unit.
# def step_into_city(positions, cluster, cluster_development_settings, cities_by_fuel):
#     a = []
#     unmoved_positions = []
#     for pos in positions:
#         adjacent_positions = cluster_extensions.get_adjacent_positions_within_cluster(pos, cluster)
#         unit_moved = False
#         for city in cities_by_fuel:
#             for city_pos in city[1]:
#                 if city_pos in adjacent_positions:
#                     direction = extensions.get_directions_to_target(pos, city_pos)
#                     a.append(cluster.cell_infos[pos].my_units[0].move(direction))
#                     unit_moved = True
#                     break
#             if unit_moved:
#                 break
#         if not unit_moved:
#             unmoved_positions.append(pos)
#     return a, unmoved_positions
