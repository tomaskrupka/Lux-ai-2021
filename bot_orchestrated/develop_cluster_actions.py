import math

import cluster_extensions
import extensions
from churn import solve_churn_with_score, get_move_actions_with_blocks


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


def build_city_tiles(cluster):
    actions = []
    blocked_empty_tiles = []
    for cell_pos, cell_info in cluster.cell_infos.items():
        if cell_info.is_empty and cell_info.my_units:
            unit = cell_info.my_units[0]
            blocked_empty_tiles.append(cell_pos)
            if unit.can_act() and unit.get_cargo_space_left() == 0:
                actions.append(unit.build_city())
    return actions, blocked_empty_tiles


def step_out_of_resources_into_adjacent_empty(cluster, cluster_development_settings, blocked_positions):
    positions_options = []
    unmoved_units_on_resource = []
    can_act_units_on_resource = []
    actions = []
    b = []

    for cell_pos, cell_info in cluster.cell_infos.items():
        if cell_info.resource and cell_info.my_units:
            if cell_info.my_units[0].can_act():
                can_act_units_on_resource.append(cell_pos)
    mined_resource = cluster_extensions.get_mined_resource(cluster_development_settings.research_level)
    for pos in can_act_units_on_resource:
        adjacent_development_positions = cluster_extensions.get_adjacent_development_positions(cluster, pos)
        # If unit at full capacity, let it move towards any resource
        considered_resource = mined_resource if cluster.cell_infos[pos].my_units[0].get_cargo_space_left() > 0 else 'URANIUM'
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
    moves, source_to_list = get_move_actions_with_blocks(positions_options, moves_solutions, cluster)
    actions += moves

    for source, towards in source_to_list:
        if source == towards:
            unmoved_units_on_resource.append(towards)
        elif cluster.cell_infos[towards].resource:  # Step may have happened outside
            b.append(towards)

    return actions, b, unmoved_units_on_resource


def step_within_resources(units_on_resource, cluster, cluster_development_settings, blocked_positions):
    mined_resource = cluster_extensions.get_mined_resource(cluster_development_settings.research_level)
    actions = []
    b = []
    # First try to move the units that are fully loaded. These can build next to unlocked resources.
    # Then move the rest.
    for cycle_loaded in [True, False]:
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

        positions_scores = dict()
        for target in cluster.cell_infos:
            min_dist_to_empty = math.inf
            for position in [p for p in cluster.development_positions]:
                # Hack: hide positions without resource from empty_development_positions to prevent trapping units
                # inside U-shaped cities. Remove this and score using real distance to empty development position (dijkstra)
                if sum(cluster.cell_infos[position].mining_potential.values()) == 0:
                    continue
                # Add position next to unlocked resources only for loaded units
                if cluster_extensions.can_mine_on_position(cluster, position, mined_resource) or cycle_loaded:
                    dist = position.distance_to(target)
                    if dist < min_dist_to_empty:
                        min_dist_to_empty = dist
            positions_scores[target] = 100 - min_dist_to_empty - 10 * (
                    cluster.cell_infos[target].my_city_tile is not None)

        moves_solutions, scores = solve_churn_with_score(positions_options, positions_scores)
        moves, source_to_list = get_move_actions_with_blocks(positions_options, moves_solutions, cluster)
        actions += moves
        for source, towards in source_to_list:
            if towards != source:
                b.append(towards)
                units_on_resource.remove(source)
    return actions, b, units_on_resource


def push_out_units_for_export(cluster, cluster_development_settings, units_surplus, blocked_positions, push_out_units):
    actions = []
    b = []
    # For each export pos try to export from any push-out position
    push_out_units_remaining = min(units_surplus, cluster_development_settings.units_export_count)
    satisfied_export_positions = set()
    for export_pos in cluster_development_settings.units_export_positions:
        if push_out_units_remaining <= 0:
            break
        if export_pos in blocked_positions:
            continue
        for unit_pos in push_out_units:
            if unit_pos.is_adjacent(export_pos):
                if cluster.cell_infos[unit_pos].my_units[0].can_act():
                    direction = extensions.get_directions_to_target(unit_pos, export_pos)
                    actions.append(cluster.cell_infos[unit_pos].my_units[0].move(direction))
                    b.append(export_pos)

                # Treat as pushed even if could not act. Otherwise another unit would be pushed out of city to fulfill this.
                push_out_units_remaining -= 1
                push_out_units.remove(unit_pos)
                satisfied_export_positions.add(export_pos)
                break

    return actions, b, push_out_units_remaining, satisfied_export_positions, push_out_units


def get_city_push_outs(cluster, cluster_development_settings, push_out_units_remaining, satisfied_export_positions,
                       push_out_units, push_out_positions):
    city_push_outs = dict()
    for export_pos in cluster_development_settings.units_export_positions:
        if push_out_units_remaining <= 0:
            break
        if export_pos in satisfied_export_positions:
            continue
        for push_pos in push_out_positions:
            adjacent_positions = cluster_extensions.get_adjacent_positions_within_cluster(push_pos, cluster)
            adjacent_positions_any = extensions.get_adjacent_positions(push_pos, cluster_development_settings.width)
            if export_pos not in adjacent_positions_any:
                continue
            unit_pushed = False
            for adj_pos in adjacent_positions:
                if cluster.cell_infos[adj_pos].my_city_tile and cluster.cell_infos[adj_pos].my_units:
                    for unit in cluster.cell_infos[adj_pos].my_units:
                        if unit not in push_out_units and unit.can_act():
                            push_out_units_remaining -= 1
                            push_out_units.append(unit)
                            unit_pushed = True
                            if adj_pos in city_push_outs:
                                city_push_outs[adj_pos].append(push_pos)
                            else:
                                city_push_outs[adj_pos] = [push_pos]
                            break
                    if unit_pushed:
                        break
            if unit_pushed:
                break

    return city_push_outs


def step_out_of_cities(cluster, cluster_development_settings, city_push_outs, blocked_positions):
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
    moves, source_to_list = get_move_actions_with_blocks(positions_options, moves_solutions, cluster)
    return moves
