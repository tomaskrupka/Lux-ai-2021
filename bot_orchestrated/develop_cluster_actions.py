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
    units_surplus = has_units - units_needed
    units_surplus_balance = units_surplus
    a = []
    for city_cell in [cell_info for cell_coords, cell_info in cluster.cell_infos.items() if cell_info.my_city_tile]:
        if city_cell.my_city_tile.can_act():
            if units_surplus_balance < 0 < units_allowance:
                a.append(city_cell.my_city_tile.build_worker())
                units_allowance -= 1
                units_surplus_balance += 1
            elif cluster_development_settings.research_level + researched < 200:
                a.append(city_cell.my_city_tile.research())
                researched += 1
    return a, units_allowance, units_surplus, researched


def pull_units_to_cities(cluster: Cluster, cities_scores, cannot_act_units_ids):
    a = []
    c = []
    for cell_pos, cell_info in cluster.cell_infos.items():
        if cell_info.my_units and not cell_info.my_city_tile:
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


def step_within_cities_into_better_mining_positions(
        cities_mineabilities,
        cluster: Cluster,
        cannot_act_units_ids):
    a = []
    c = []
    for city_id in cities_mineabilities:
        # find best mining position
        max_mineability = -math.inf
        best_mining_pos = None
        for pos, mineability in cities_mineabilities[city_id].items():
            if mineability > max_mineability:
                best_mining_pos = pos
                max_mineability = mineability

        for pos in cities_mineabilities[city_id]:
            if cluster.cell_infos[pos].my_units:
                can_act_units_on_pos = [u for u in cluster.cell_infos[pos].my_units if u.id not in cannot_act_units_ids]
                if can_act_units_on_pos:
                    units_moved = False
                    all_directions = extensions.get_all_directions_to_target(pos, best_mining_pos)
                    for direction in all_directions:
                        if direction != 'c':
                            new_pos = extensions.get_new_position(pos, direction)
                            if new_pos in cities_mineabilities[city_id]:
                                for unit in can_act_units_on_pos:
                                    a.append(unit.move(direction))
                                    c.append(unit.id)
                                units_moved = True
                                break
                    if not units_moved:
                        adjacent_positions = cluster_extensions.get_adjacent_positions_within_cluster(pos, cluster)
                        for adj_pos in adjacent_positions:
                            if adj_pos in cities_mineabilities[city_id] and cities_mineabilities[city_id][adj_pos] > cities_mineabilities[city_id][pos]:
                                for unit in can_act_units_on_pos:
                                    direction = extensions.get_directions_to_target(pos, adj_pos)
                                    a.append(unit.move(direction))
                                    c.append(unit.id)
    return a, c


def build_city_tiles(cluster, units_taken_actions_ids):
    a = []
    b = []
    c = []
    for cell_pos, cell_info in cluster.cell_infos.items():
        if cell_info.is_empty and cell_info.my_units:
            unit = cell_info.my_units[0]
            b.append(cell_pos)
            if unit.can_act() and unit.get_cargo_space_left() == 0 and unit.id not in units_taken_actions_ids:
                c.append(unit.id)
                a.append(unit.build_city())
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
            positions_scores[option] = 1
    moves_solutions, scores = solve_churn_with_score(positions_options, positions_scores)
    moves, source_to_list, c = get_move_actions_with_blocks(positions_options, moves_solutions, cluster)
    a += moves

    for source, towards in source_to_list:
        if source == towards:
            unmoved_units_on_resource.append(towards)
        # elif cluster.cell_infos[towards].resource:  # Step may have happened outside
        else:
            b.append(towards)
            # c.append(source)

    return a, b, c, unmoved_units_on_resource


def step_within_resources(units_on_resource, cluster, cluster_development_settings, blocked_positions):
    mined_resource = cluster_extensions.get_mined_resource(cluster_development_settings.research_level)
    a = []
    b = []
    c = []

    # Hack: hide positions without resource from empty_development_positions to prevent trapping units
    # inside U-shaped cities. Remove this and score using real distance to empty development position (dijkstra)
    mineable_development_positions = [p for p in cluster.development_positions if
                                      sum(cluster.cell_infos[p].mining_potential.values()) > 0]

    if mineable_development_positions:

        # TODO: Cannot solve churn separately for two subsets of units. Leads to collisions.

        # First try to move the units that are fully loaded. These can build next to locked resources. Then move the rest.
        for cycle_loaded in [True, False]:
            positions_scores = dict()
            for target in cluster.cell_infos:
                min_dist_to_empty = math.inf
                for position in mineable_development_positions:
                    # Add position next to unlocked resources only for loaded units
                    can_mine_on_position = cluster_extensions.can_mine_on_position(cluster, position, mined_resource)
                    if cycle_loaded or can_mine_on_position:
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
                    if adj_cell_info.resource and adj_pos not in blocked_positions and adj_pos not in b:
                        options.append(adj_pos)
                if len(options) > 0:
                    positions_options.append([position, options])

            moves_solutions, scores = solve_churn_with_score(positions_options, positions_scores)
            moves, source_to_list, cannot_act_ids = get_move_actions_with_blocks(positions_options, moves_solutions,
                                                                                 cluster)
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
                if unit.id not in cannot_act_units_ids:
                    direction = extensions.get_directions_to_target(unit_pos, export_pos)
                    a.append(unit.move(direction))
                    b.append(export_pos)
                    c.append(unit.id)
                    pushed_out_units_positions.append(unit_pos)
                    satisfied_export_positions.append(export_pos)

                # Count as pushed even if could not act. Otherwise another unit would be pushed out of city to fulfill this.
                units_to_push_out -= 1
                break

    return a, b, c, satisfied_export_positions


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


def step_out_of_cities_into_mining(cluster, cluster_development_settings, blocked_positions, cannot_act_units_ids):
    mined_resource = cluster_extensions.get_mined_resource(cluster_development_settings.research_level)
    positions_options = []

    for cell_pos, cell_info in cluster.cell_infos.items():
        if cell_info.my_city_tile and cell_info.my_units:
            # free adjacent mining positions
            cell_pos_options = [p for p in
                                cluster_extensions.get_adjacent_mining_positions(cluster, cell_pos, mined_resource) if
                                not cluster.cell_infos[p].my_city_tile and
                                not cluster.cell_infos[p].opponent_city_tile and
                                p not in blocked_positions]
            if len(cell_pos_options) > 0:
                for unit in cell_info.my_units:
                    if unit.id not in cannot_act_units_ids:
                        positions_options.append([cell_pos, cell_pos_options])
    positions_scores = dict()
    for position, options in positions_options:
        for option in options:
            positions_scores[option] = cluster_extensions.get_mining_potential_aggregate(
                cluster.cell_infos[option].mining_potential, mined_resource)
    moves_solutions, scores = solve_churn_with_score(positions_options, positions_scores)
    a, source_to_list, c = get_move_actions_with_blocks(positions_options, moves_solutions, cluster)
    b = []
    for source, towards in source_to_list:
        if towards != source:
            b.append(towards)
    return a, b, c


# TODO: step into city that benefits the most from this unit.
def step_into_city(positions, cluster, cluster_development_settings, cities_by_fuel):
    a = []
    unmoved_positions = []
    for pos in positions:
        adjacent_positions = cluster_extensions.get_adjacent_positions_within_cluster(pos, cluster)
        unit_moved = False
        for city in cities_by_fuel:
            for city_pos in city[1]:
                if city_pos in adjacent_positions:
                    direction = extensions.get_directions_to_target(pos, city_pos)
                    a.append(cluster.cell_infos[pos].my_units[0].move(direction))
                    unit_moved = True
                    break
            if unit_moved:
                break
        if not unit_moved:
            unmoved_positions.append(pos)
    return a, unmoved_positions
