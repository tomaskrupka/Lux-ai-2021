import math

import cluster_extensions
import extensions
from cluster import Cluster
from churn import solve_churn_with_score, get_move_actions_with_blocks
from lux.game_objects import Unit


def build_workers_or_research(cluster, cluster_development_settings):
    units_allowance = cluster_development_settings.units_build_allowance
    researched = 0  # Prevent researching past 200 here and in other clusters
    units_needed, has_units = cluster_extensions.get_units_needed_for_maintenance(cluster)
    units_surplus = has_units - units_needed - cluster_development_settings.units_export_count
    units_surplus_balance = units_surplus
    actions = []
    for city_cell in [cell_info for cell_coords, cell_info in cluster.cell_infos.items() if cell_info.my_city_tile]:
        if city_cell.my_city_tile.can_act():
            if units_surplus_balance < 0 < units_allowance:
                actions.append(city_cell.my_city_tile.build_worker())
                units_allowance -= 1
                units_surplus_balance += 1
            elif cluster_development_settings.research_level + researched < 200:
                actions.append(city_cell.my_city_tile.research())
                researched += 1
    return actions, units_allowance, units_surplus, researched


def pull_units_to_cities(cluster: Cluster, forbidden_units_positions, units_taken_action_ids):
    # identify cities
    cities = dict()  # id = city
    for cell_pos, cell_info in cluster.cell_infos.items():
        if cell_info.my_city:
            cities[cell_info.my_city.cityid] = cell_info.my_city
    # score cities
    cities_scores = dict()  # id = city_score
    for city_id, city in cities.items():
        city_score = 0
        for city_tile in city.citytiles:
            city_score += 1 - len(cluster.cell_infos[city_tile.pos].my_units)
        cities_scores[city_id] = city_score
    # generate actions
    a = []
    uta = []
    for cell_pos, cell_info in cluster.cell_infos.items():
        if cell_info.my_units and not cell_info.my_city_tile and cell_pos not in forbidden_units_positions:
            unit = cell_info.my_units[0]
            if unit.id in units_taken_action_ids:
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
            uta.append(unit.id)
    return a, uta


def build_city_tiles(cluster, units_taken_actions_ids):
    actions = []
    blocked_empty_tiles = []
    uta = []
    for cell_pos, cell_info in cluster.cell_infos.items():
        if cell_info.is_empty and cell_info.my_units:
            unit = cell_info.my_units[0]
            blocked_empty_tiles.append(cell_pos)
            if unit.can_act() and unit.get_cargo_space_left() == 0 and unit.id not in units_taken_actions_ids:
                uta.append(unit.id)
                actions.append(unit.build_city())
    return actions, blocked_empty_tiles, uta


def step_out_of_resources_into_adjacent_empty(cluster, cluster_development_settings, blocked_positions,
                                              units_taken_actions_ids):
    positions_options = []
    unmoved_units_on_resource = []
    can_act_units_on_resource = []
    a = []
    b = []
    # c = []

    for cell_pos, cell_info in cluster.cell_infos.items():
        if cell_info.resource and cell_info.my_units:
            unit = cell_info.my_units[0]
            if unit.can_act() and unit.id not in units_taken_actions_ids:
                can_act_units_on_resource.append(cell_pos)
    mined_resource = cluster_extensions.get_mined_resource(cluster_development_settings.research_level)
    for pos in can_act_units_on_resource:
        adjacent_development_positions = cluster_extensions.get_adjacent_development_positions(cluster, pos)
        # If unit at full capacity, let it move towards any resource
        considered_resource = mined_resource if cluster.cell_infos[pos].my_units[
                                                    0].get_cargo_space_left() > 0 else 'URANIUM'
        adjacent_mining_positions = cluster_extensions.get_adjacent_mining_positions(cluster, pos, considered_resource)
        if len(adjacent_development_positions) > 0:
            positions_options.append([pos, [p for p in adjacent_development_positions if
                                            p not in blocked_positions and
                                            p in adjacent_mining_positions]])
        else:
            # had no adjacent development position
            unmoved_units_on_resource.append(pos)

    positions_scores = dict()
    for position, options in positions_options:
        for option in options:
            positions_scores[option] = 1
    moves_solutions, scores = solve_churn_with_score(positions_options, positions_scores)
    moves, source_to_list, uta = get_move_actions_with_blocks(positions_options, moves_solutions, cluster)
    a += moves

    for source, towards in source_to_list:
        if source == towards:
            unmoved_units_on_resource.append(towards)
        # elif cluster.cell_infos[towards].resource:  # Step may have happened outside
        else:
            b.append(towards)
            # c.append(source)

    return a, b, uta, unmoved_units_on_resource


def step_within_resources(units_on_resource, cluster, cluster_development_settings, blocked_positions):
    mined_resource = cluster_extensions.get_mined_resource(cluster_development_settings.research_level)
    actions = []
    b = []
    uta = []

    # Hack: hide positions without resource from empty_development_positions to prevent trapping units
    # inside U-shaped cities. Remove this and score using real distance to empty development position (dijkstra)
    mineable_development_positions = [p for p in cluster.development_positions if
                                      sum(cluster.cell_infos[p].mining_potential.values()) == 0]

    if mineable_development_positions:

        # First try to move the units that are fully loaded. These can build next to unlocked resources. Then move the rest.
        for cycle_loaded in [True, False]:
            positions_scores = dict()
            for target in cluster.cell_infos:
                min_dist_to_empty = math.inf
                for position in mineable_development_positions:
                    # Add position next to unlocked resources only for loaded units
                    if cycle_loaded or cluster_extensions.can_mine_on_position(cluster, position, mined_resource):
                        dist = position.distance_to(target)
                        if dist < min_dist_to_empty:
                            min_dist_to_empty = dist
                positions_scores[target] = 100 - min_dist_to_empty - 10 * (
                        cluster.cell_infos[target].my_city_tile is not None)

            positions_options = []
            for position in units_on_resource:
                is_loaded_unit = cluster.cell_infos[position].my_units[0].get_cargo_space_left() == 0
                if cycle_loaded != is_loaded_unit:
                    continue
                options = []
                for adj_pos in cluster_extensions.get_adjacent_positions_within_cluster(position, cluster):
                    adj_cell_info = cluster.cell_infos[adj_pos]
                    if adj_cell_info.resource and adj_pos not in blocked_positions:
                        options.append(adj_pos)
                if len(options) > 0:
                    positions_options.append([position, options])

            moves_solutions, scores = solve_churn_with_score(positions_options, positions_scores)
            moves, source_to_list, cannot_act_ids = get_move_actions_with_blocks(positions_options, moves_solutions, cluster)
            actions += moves
            uta += cannot_act_ids
            for source, towards in source_to_list:
                if towards != source:
                    b.append(towards)
                    units_on_resource.remove(source)

    return actions, b, uta, units_on_resource


def push_out_units_for_export(cluster, cluster_development_settings, units_to_push_out, blocked_positions,
                              units_taken_action_ids,
                              push_out_units):
    a = []
    b = []
    uta = []
    satisfied_export_positions = []

    pushed_out_units_positions = []
    # For each export pos try to export any push-out unit
    for export_pos in cluster_development_settings.units_export_positions:
        if units_to_push_out <= 0:
            break
        if export_pos in blocked_positions:
            continue
        for unit_pos in push_out_units:
            if unit_pos.is_adjacent(export_pos) and unit_pos not in pushed_out_units_positions:
                unit = cluster.cell_infos[unit_pos].my_units[0]
                if unit.can_act() and unit not in units_taken_action_ids:
                    direction = extensions.get_directions_to_target(unit_pos, export_pos)
                    a.append(unit.move(direction))
                    b.append(export_pos)
                    uta.append(unit.id)
                    pushed_out_units_positions.append(unit_pos)
                    satisfied_export_positions.append(export_pos)

                # Count as pushed even if could not act. Otherwise another unit would be pushed out of city to fulfill this.
                units_to_push_out -= 1
                break

    return a, b, uta, satisfied_export_positions


def push_out_from_cities(
        cluster,
        blocked_positions,
        count_to_push_out,
        push_out_positions,
        units_taken_actions_ids):
    a = []
    b = []
    uta = []

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
                    if unit.can_act() and unit.id not in units_taken_actions_ids and unit.id not in uta:  # unit can be visited multiple times as adjacent to different push out positions.
                        direction = extensions.get_directions_to_target(adj_pos, push_pos)
                        a.append(unit.move(direction))
                        b.append(push_pos)
                        uta.append(unit.id)
                        count_to_push_out -= 1
                        unit_pushed = True
                        break
                if unit_pushed:
                    break

    return a, b, uta


def step_out_of_cities_into_mining(cluster, cluster_development_settings, blocked_positions, units_taken_action_ids):
    mined_resource = cluster_extensions.get_mined_resource(cluster_development_settings.research_level)
    positions_options = []
    for cell_pos, cell_info in cluster.cell_infos.items():
        if cell_info.my_city_tile and cell_info.my_units:
            adjacent_mining_positions = [p for p in cluster_extensions.get_adjacent_mining_positions(cluster, cell_pos,
                                                                                                     mined_resource) if
                                         not cluster.cell_infos[p].my_city_tile and
                                         not cluster.cell_infos[p].opponent_city_tile]
            free_adj_mining_positions = [p for p in adjacent_mining_positions if
                                         p not in blocked_positions]
            if len(free_adj_mining_positions) > 0:
                if cell_pos in city_push_outs:
                    free_adj_mining_positions += city_push_outs[cell_pos]
                positions_options.append([cell_pos, free_adj_mining_positions])
            else:
                if cell_pos in city_push_outs:
                    positions_options.append([cell_pos, city_push_outs[cell_pos]])
    positions_scores = dict()
    for position, options in positions_options:
        for option in options:
            positions_scores[option] = cluster.cell_infos[option].mining_potential['WOOD']
    for city, push_outs in city_push_outs.items():
        for push_out in push_outs:
            positions_scores[push_out] = 1000
    moves_solutions, scores = solve_churn_with_score(positions_options, positions_scores)
    moves, source_to_list, uta = get_move_actions_with_blocks(positions_options, moves_solutions, cluster)
    return moves


# TODO: step into city that benefits the most from this unit.
def step_into_city(positions, cluster, cluster_development_settings, cities_by_fuel):
    actions = []
    unmoved_positions = []
    for pos in positions:
        adjacent_positions = cluster_extensions.get_adjacent_positions_within_cluster(pos, cluster)
        unit_moved = False
        for city in cities_by_fuel:
            for city_pos in city[1]:
                if city_pos in adjacent_positions:
                    direction = extensions.get_directions_to_target(pos, city_pos)
                    actions.append(cluster.cell_infos[pos].my_units[0].move(direction))
                    unit_moved = True
                    break
            if unit_moved:
                break
        if not unit_moved:
            unmoved_positions.append(pos)
    return actions, unmoved_positions
