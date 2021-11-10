import math

import develop_cluster_actions
import extensions
from cluster import Cluster, ClusterDevelopmentSettings
from lux.game_map import Position


def develop_cluster(cluster: Cluster, cluster_development_settings: ClusterDevelopmentSettings):
    actions = []  # To submit to the agent.
    units_allowance: int  # How many units can other clusters build.
    units_surplus: int  # Units needed in this cluster - units_export_count.
    researched: int  # Prevent researching past 200 here and in other clusters.
    cannot_act_units: list  # Units that need to cool down.
    blocked_tiles = []  # Where my units cannot move. Dynamically update as moves happen.

    cannot_act_units = develop_cluster_actions.get_cannot_act_units(cluster)
    blocked_tiles += cannot_act_units

    # CITY TILE ACTIONS

    a, units_allowance, units_surplus, researched = develop_cluster_actions.build_workers_or_research(
        cluster, cluster_development_settings)
    actions += a

    # BUILD CITY TILES
    # TODO: exclude units coming to the city with resources.

    a, b = develop_cluster_actions.build_city_tiles(cluster)
    actions += a
    blocked_tiles += b

    # step out of resource tiles where adjacent empty
    positions_options = []
    units_on_resource = []
    can_act_units_on_resource = []

    for cell_pos, cell_info in cluster.cell_infos.items():
        if cell_info.resource and cell_info.my_units:
            if cell_info.my_units[0].can_act():
                can_act_units_on_resource.append(cell_pos)
    mined_resource = get_mined_resource(cluster_development_settings.research_level)
    for pos in can_act_units_on_resource:
        adjacent_development_positions = get_adjacent_development_positions(cluster, pos)
        adjacent_mining_positions = get_adjacent_mining_positions(cluster, pos, mined_resource)
        if len(adjacent_development_positions) > 0:
            positions_options.append([pos, [p for p in adjacent_development_positions if
                                            p not in cannot_act_units and
                                            p not in blocked_tiles and
                                            p in adjacent_mining_positions]])
        else:
            # had no adjacent development position
            units_on_resource.append(pos)

    positions_scores = dict()
    for position, options in positions_options:
        for option in options:
            positions_scores[option] = 1
    moves_solutions, scores = solve_churn_with_score(positions_options, positions_scores)
    moves, source_to_list = get_move_actions_with_blocks(positions_options, moves_solutions, cluster)
    actions += moves

    for source, towards in source_to_list:
        # had some adjacent development positions, but others took them
        if towards in cluster.resource_positions:
            units_on_resource.append(towards)
        elif cluster.cell_infos[towards].is_empty:
            blocked_tiles.append(towards)

    # figure out empty development positions, account for blocked empty tiles
    empty_development_positions = []
    for position in cluster.development_positions:
        if position not in blocked_tiles:
            is_position_free = True
            for move, solutions in moves_solutions.items():
                if position in solutions:
                    is_position_free = False
                    continue
            if is_position_free:
                empty_development_positions.append(position)

    # take a step from resource to some other resource if step out was unsuccessful
    if units_on_resource:
        moves, units_on_resource = step_within_resources(units_on_resource, cluster, empty_development_positions,
                                                         cannot_act_units, mined_resource)
        actions += moves

    # push out units for export
    push_out_units = []  # units on push out positions
    push_out_positions = []  # positions to push from to export positions
    for cell_pos, cell_info in cluster.cell_infos.items():
        adjacent_positions_any = extensions.get_adjacent_positions(cell_pos, cluster_development_settings.width)
        adjacent_positions_cluster = get_adjacent_positions_within_cluster(cell_pos, cluster)
        is_next_to_city = any(pos for pos in adjacent_positions_cluster if cluster.cell_infos[pos].my_city_tile)
        is_next_to_export_position = any(
            pos for pos in adjacent_positions_any if pos in cluster_development_settings.units_export_positions)
        is_push_out_position = is_next_to_city and is_next_to_export_position
        if is_push_out_position:
            push_out_positions.append(cell_pos)
            if cell_info.my_units and cell_info.my_units[0].get_cargo_space_left() == 100:
                push_out_units.append(cell_pos)
                if cell_info.my_city_tile:
                    print('error. push out unit in a city.')

    # For each export pos try to export from any push-out position
    push_out_units_remaining = min(units_surplus + 1, cluster_development_settings.units_export_count)
    satisfied_export_positions = set()
    for export_pos in cluster_development_settings.units_export_positions:
        if push_out_units_remaining <= 0:
            break
        for unit_pos in push_out_units:
            if unit_pos.is_adjacent(export_pos):
                direction = extensions.get_directions_to_target(unit_pos, export_pos)
                if cluster.cell_infos[unit_pos].my_units[0].can_act():
                    actions.append(cluster.cell_infos[unit_pos].my_units[0].move(direction))
                    blocked_tiles.remove(unit_pos)
                # Treat as pushed even if could not act. Otherwise another unit would be pushed out of city to fulfill this.
                push_out_units_remaining -= 1
                push_out_units.remove(unit_pos)
                satisfied_export_positions.add(export_pos)
                break

    # If we need to export more units,
    # generate moves from cities towards push-out positions next to unsatisfied exports.
    pushed_out_units = []
    city_push_outs = dict()
    for export_pos in cluster_development_settings.units_export_positions:
        if push_out_units_remaining <= 0:
            break
        if export_pos in satisfied_export_positions:
            continue
        for push_pos in push_out_positions:
            adjacent_positions = get_adjacent_positions_within_cluster(push_pos, cluster)
            adjacent_positions_any = extensions.get_adjacent_positions(push_pos, cluster_development_settings.width)
            if export_pos not in adjacent_positions_any:
                continue
            unit_pushed = False
            for adj_pos in adjacent_positions:
                if cluster.cell_infos[adj_pos].my_city_tile and cluster.cell_infos[adj_pos].my_units:
                    for unit in cluster.cell_infos[adj_pos].my_units:
                        if unit not in pushed_out_units and unit.can_act():
                            push_out_units_remaining -= 1
                            pushed_out_units.append(unit)
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

    # step out of cities into mining and push-out positions
    positions_options = []
    for cell_pos, cell_info in cluster.cell_infos.items():
        if cell_info.my_city_tile and cell_info.my_units:
            adjacent_mining_positions = [p for p in get_adjacent_mining_positions(cluster, cell_pos, mined_resource) if
                                         not cluster.cell_infos[p].my_city_tile and
                                         not cluster.cell_infos[p].opponent_city_tile]
            free_adj_mining_positions = [p for p in adjacent_mining_positions if
                                         p not in units_on_resource and
                                         p not in cannot_act_units and
                                         p not in blocked_tiles]
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

    actions += moves

    actions_allowance = [actions, units_allowance, researched]
    return actions_allowance


def get_mined_resource(research_level):
    mined_resource = 'WOOD'
    if research_level >= 50:
        mined_resource = 'COAL'
    if research_level >= 200:
        mined_resource = 'URANIUM'
    return mined_resource


#
# def step_out_of_resources_into_mining_positions(units_on_resource, cluster, cluster_development_settings, blocked_positions):
#     # step out of resource tiles where adjacent empty
#     positions_options = []
#     units_on_resource = []
#     can_act_units_on_resource = []
#     actions = []
#
#     for cell_pos, cell_info in cluster.cell_infos.items():
#         if cell_info.resource and cell_info.my_units:
#             if cell_info.my_units[0].can_act():
#                 can_act_units_on_resource.append(cell_pos)
#     mined_resource = get_mined_resource(cluster_development_settings.research_level)
#     for pos in can_act_units_on_resource:
#         adjacent_development_positions = get_adjacent_development_positions(cluster, pos)
#         adjacent_mining_positions = get_adjacent_mining_positions(cluster, pos, mined_resource)
#         if len(adjacent_development_positions) > 0:
#             positions_options.append([pos, [p for p in adjacent_development_positions if
#                                             p not in blocked_positions and
#                                             p in adjacent_mining_positions]])
#         else:
#             # had no adjacent development position
#             units_on_resource.append(pos)
#
#     positions_scores = dict()
#     for position, options in positions_options:
#         for option in options:
#             positions_scores[option] = 1
#     moves_solutions, scores = solve_churn_with_score(positions_options, positions_scores)
#     moves, source_to_list = get_move_actions_with_blocks(positions_options, moves_solutions, cluster)
#     actions += moves
#
#     for source, towards in source_to_list:
#         # had some adjacent development positions, but others took them
#         if towards in cluster.resource_positions:
#             units_on_resource.append(towards)
#         elif cluster.cell_infos[towards].is_empty:
#             blocked_empty_tiles.append(towards)


# Steps within resources towards empty development positions.
def step_within_resources(units_on_resource, cluster: Cluster, empty_development_positions, blocked_tiles,
                          mined_resource):
    actions = []
    new_moves = []  # cannot append new moves directly to units_on_resources as both rounds use that list
    # First try to move the units that are fully loaded. These can build next to unlocked resources.
    # Then move the rest.
    for cycle_loaded in [True, False]:
        positions_options = []
        for position in units_on_resource:
            is_loaded_unit = cluster.cell_infos[position].my_units[0].get_cargo_space_left() == 0
            if cycle_loaded != is_loaded_unit:
                continue
            options = []
            for adj_pos in get_adjacent_positions_within_cluster(position, cluster):
                cell_info = cluster.cell_infos[adj_pos]
                if cell_info.resource and not cell_info.opponent_city_tile and adj_pos not in blocked_tiles:
                    options.append(adj_pos)
            if len(options) > 0:
                positions_options.append([position, options])

        positions_scores = dict()
        for target in cluster.cell_infos:
            min_dist_to_empty = math.inf
            for position in empty_development_positions:
                # Hack: hide positions without resource from empty_development_positions to prevent trapping units
                # inside U-shaped cities. Remove this and score using real distance to empty development position (dijkstra)
                if sum(cluster.cell_infos[position].mining_potential.values()) == 0:
                    continue
                # Add position next to unlocked resources only for loaded units
                if can_mine_on_position(cluster, position, mined_resource) or cycle_loaded:
                    dist = position.distance_to(target)
                    if dist < min_dist_to_empty:
                        min_dist_to_empty = dist
            positions_scores[target] = 100 - min_dist_to_empty - 10 * (
                    cluster.cell_infos[target].my_city_tile is not None)

        moves_solutions, scores = solve_churn_with_score(positions_options, positions_scores)
        moves, source_to_list = get_move_actions_with_blocks(positions_options, moves_solutions, cluster)
        actions += moves
        for source, towards in source_to_list:
            units_on_resource.remove(source)
            if towards in cluster.resource_positions:
                new_moves.append(towards)
    units_on_resource += new_moves
    return actions, units_on_resource


def solve_churn_with_score(positions_options: [], positions_scores: []):
    move_solutions = dict()
    high_score = -math.inf
    valid_positions_options = []
    for position, options in positions_options:
        if len(options) > 0:
            valid_positions_options.append([position, options])
    if len(valid_positions_options) == 0:
        return move_solutions, 0
    for position, options in valid_positions_options:
        for option in options:
            positions_options_reduction = get_position_options_reduction(valid_positions_options, position,
                                                                         option).items()
            if len(positions_options_reduction) > 0:
                move_solutions_reduction, score = solve_churn_with_score(positions_options_reduction, positions_scores)
                pos_opt_score = score + positions_scores[option]
                if pos_opt_score > high_score:
                    high_score = pos_opt_score
                    move_solutions = move_solutions_reduction
                    if position in move_solutions:
                        move_solutions[position].append(option)
                    else:
                        move_solutions[position] = [option]
            else:
                pos_opt_score = positions_scores[option]
                if pos_opt_score > high_score:
                    high_score = pos_opt_score
                    move_solutions[position] = [option]

    return move_solutions, high_score


def get_position_options_reduction(positions_options, pos_to_remove, opt_to_remove):
    positions_options_reduction = dict()
    for position, options in positions_options:
        if position != pos_to_remove:
            for option in options:
                if option != opt_to_remove:
                    if position in positions_options_reduction:
                        positions_options_reduction[position].append(option)
                    else:
                        positions_options_reduction[position] = [option]
    return positions_options_reduction


def get_move_actions_with_blocks(positions_options, moves_solutions, cluster):
    positions_units = dict()
    for position, options in positions_options:
        if position in positions_units:
            used_units = len(positions_units[position])
            positions_units[position].append(cluster.cell_infos[position].my_units[used_units])
        else:
            positions_units[position] = [cluster.cell_infos[position].my_units[0]]
    blocked_positions = []
    actions = []
    for position in positions_units:
        if position in moves_solutions:
            for move, unit in zip(moves_solutions[position], positions_units[position]):
                direction = extensions.get_directions_to_target(position, move)
                actions.append(unit.move(direction))
                blocked_positions.append((position, move))
            if len(moves_solutions[position]) < len(positions_units[position]):
                blocked_positions.append((position, position))
        else:
            blocked_positions.append((position, position))
    return actions, blocked_positions


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


def get_adjacent_development_positions(cluster: Cluster, p: Position):
    adjacent_development_positions = []
    for q in cluster.development_positions:
        if p.is_adjacent(q):
            adjacent_development_positions.append(q)
    return adjacent_development_positions


def get_adjacent_mining_positions(cluster: Cluster, p: Position, mined_resource):
    adjacent_mining_positions = []
    for cell_pos in cluster.cell_infos:
        if p.is_adjacent(cell_pos) and (can_mine_on_position(cluster, cell_pos, mined_resource)):
            adjacent_mining_positions.append(cell_pos)
    return adjacent_mining_positions


def can_mine_on_position(cluster: Cluster, position: Position, mined_resource):
    cell_info = cluster.cell_infos[position]
    can_mine_here = cell_info.mining_potential['WOOD'] > 0 or \
                    (cell_info.mining_potential['COAL'] > 0 and not mined_resource == 'WOOD') or \
                    (cell_info.mining_potential['URANIUM'] > 0 and mined_resource == 'URANIUM')
    return can_mine_here


def get_closest_development_position(cluster: Cluster, xy):
    min_dist = math.inf
    closest_position = None
    for (x, y) in cluster.development_positions:
        dist = abs(x - xy[0]) + abs(y - xy[1])
        if dist < min_dist:
            closest_position = (x, y)
            min_dist = dist
    return closest_position


def get_adjacent_positions_within_cluster(p: Position, c: Cluster):
    adjacent_positions = [Position(a, b) for (a, b) in [(p.x - 1, p.y), (p.x + 1, p.y), (p.x, p.y - 1), (p.x, p.y + 1)]]
    return [p for p in adjacent_positions if p in c.cell_infos]
