import math
import extensions
from lux.game import Game
from lux.game_constants import GAME_CONSTANTS
from lux.game_map import Resource, Position
from lux.game_objects import Player, CityTile, City, Unit


class CellInfo:
    def __init__(
            self,
            position: Position,
            is_empty: bool,
            my_city_tile: CityTile,
            opponent_city_tile: CityTile,
            my_city: City,
            opponent_city: City,
            resource: Resource,
            my_units: list,
            opponent_units: list):
        self.adjacent_positions = None
        self.mining_potential = None
        self.position = position
        self.is_empty = is_empty
        self.my_city_tile = my_city_tile
        self.opponent_city_tile = opponent_city_tile
        self.my_city = my_city
        self.opponent_city = opponent_city
        self.resource = resource
        self.my_units = my_units
        self.opponent_units = opponent_units


class ClusterDevelopmentSettings:
    def __init__(self,
                 units_build_allowance: int,
                 units_export_positions: list,
                 units_export_count: int,
                 upcoming_cycles: list,
                 research_level: int,
                 width: int):
        self.units_build_allowance = units_build_allowance
        self.units_export_positions = units_export_positions
        self.units_export_count = units_export_count
        self.upcoming_cycles = upcoming_cycles
        self.research_level = research_level
        self.width = width


class Cluster:

    def __init__(self, cluster_id, non_empty_coordinates, game_state: Game, my_city_tiles, opponent_city_tiles,
                 my_units,
                 opponent_units):
        self.cluster_id = cluster_id
        self.cell_infos = dict()
        self.resource_positions = set()
        adjacent_positions = extensions.get_adjacent_positions_cluster(non_empty_coordinates, game_state.map_width)

        all_cluster_coordinates = adjacent_positions.union(non_empty_coordinates)
        self.development_positions = [pos for pos in all_cluster_coordinates if pos not in non_empty_coordinates]
        self.is_me_present = False
        self.is_opponent_present = False
        for p in all_cluster_coordinates:
            cell_info = game_state.map.get_cell_by_pos(p)
            my_city_tile = my_city_tiles[p][1] if p in my_city_tiles else None
            opponent_city_tile = opponent_city_tiles[p][1] if p in opponent_city_tiles else None
            has_resource = cell_info.has_resource()
            if has_resource:
                self.resource_positions.add(p)
            cell_info = CellInfo(
                position=p,
                my_city_tile=my_city_tile,
                opponent_city_tile=opponent_city_tile,
                my_city=my_city_tiles[p][0] if my_city_tile is not None else None,
                opponent_city=opponent_city_tiles[p][0] if opponent_city_tile is not None else None,
                resource=cell_info.resource,
                is_empty=my_city_tile is None and opponent_city_tile is None and not has_resource,
                my_units=my_units[p] if p in my_units else [],
                opponent_units=opponent_units[p] if p in opponent_units else []
            )
            self.cell_infos[p] = cell_info
            if cell_info.my_city_tile or cell_info.my_units:
                self.is_me_present = True
            if cell_info.opponent_city_tile or cell_info.opponent_units:
                self.is_opponent_present = True
            self.my_city_tiles = [p for p in self.cell_infos if self.cell_infos[p].my_city_tile]
            self.opponent_city_tiles = [p for p in self.cell_infos if self.cell_infos[p].opponent_city_tile]

        for cell_pos in self.cell_infos:
            resource_amounts = dict(WOOD=0, COAL=0, URANIUM=0)
            adjacent_positions = extensions.get_adjacent_positions(cell_pos, game_state.map_width)
            self.cell_infos[cell_pos].adjacent_positions = adjacent_positions
            for p in adjacent_positions + [cell_pos]:
                if p in self.cell_infos:
                    cell_info = self.cell_infos[p]
                    if cell_info.resource is None:
                        continue
                    else:
                        for RESOURCE_TYPE, resource_type in GAME_CONSTANTS['RESOURCE_TYPES'].items():
                            if cell_info.resource.type == resource_type:
                                amount = cell_info.resource.amount
                                collection_rate = GAME_CONSTANTS['PARAMETERS']['WORKER_COLLECTION_RATE'][RESOURCE_TYPE]
                                resource_amounts[
                                    RESOURCE_TYPE] += amount if amount < collection_rate else collection_rate
                                break
            self.cell_infos[cell_pos].mining_potential = resource_amounts


def develop_cluster(cluster: Cluster, cluster_development_settings: ClusterDevelopmentSettings):
    actions = []
    remaining_new_units_allowance = cluster_development_settings.units_build_allowance

    units_needed, has_units = get_units_needed(cluster)

    units_surplus = has_units - units_needed - cluster_development_settings.units_export_count
    units_surplus_balance = units_surplus

    # Build workers or research
    city_cell: CellInfo
    for city_cell in [cell_info for cell_coords, cell_info in cluster.cell_infos.items() if cell_info.my_city_tile]:
        if city_cell.my_city_tile.can_act():
            if units_surplus_balance < 0 < remaining_new_units_allowance:
                actions.append(city_cell.my_city_tile.build_worker())
                remaining_new_units_allowance -= 1
                units_surplus_balance += 1
            else:
                actions.append(city_cell.my_city_tile.research())

    cannot_act_units = []
    for cell_pos, cell_info in cluster.cell_infos.items():
        if not cell_info.my_city_tile:
            if cell_info.my_units:
                if not cell_info.my_units[0].can_act():
                    cannot_act_units.append(cell_pos)

    # build city tiles
    # TODO: exclude units coming to the city with resources.

    blocked_empty_tiles = []
    for cell_pos, cell_info in cluster.cell_infos.items():
        if cell_info.is_empty and cell_info.my_units:
            unit = cell_info.my_units[0]
            blocked_empty_tiles.append(cell_pos)
            if unit.can_act() and unit.get_cargo_space_left() == 0:
                actions.append(unit.build_city())

    # step out of resource tiles where adjacent empty
    positions_options = []
    units_on_resource = []
    can_act_units_on_resource = []

    for cell_pos, cell_info in cluster.cell_infos.items():
        if cell_info.resource and cell_info.my_units:
            if cell_info.my_units[0].can_act():
                can_act_units_on_resource.append(cell_pos)
    for pos in can_act_units_on_resource:
        adjacent_development_positions = get_adjacent_development_positions(cluster, pos)
        if len(adjacent_development_positions) > 0:
            positions_options.append([pos, [p for p in adjacent_development_positions if
                                            p not in cannot_act_units and p not in blocked_empty_tiles]])
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
            blocked_empty_tiles.append(towards)

    # take a step from resource to some other resource if step out was unsuccessful
    empty_development_positions = []
    for position in cluster.development_positions:
        if position not in blocked_empty_tiles:
            is_position_free = True
            for move, solutions in moves_solutions.items():
                if position in solutions:
                    is_position_free = False
                    continue
            if is_position_free:
                empty_development_positions.append(position)

    positions_options = []
    for position in units_on_resource:
        options = []
        for adj_pos in get_adjacent_positions_within_cluster(position, cluster):
            cell_info = cluster.cell_infos[adj_pos]
            if not cell_info.opponent_city_tile and adj_pos not in cannot_act_units and adj_pos not in blocked_empty_tiles:
                options.append(adj_pos)
        if len(options) > 0:
            positions_options.append([position, options])

    positions_scores = dict()
    for target in cluster.cell_infos:
        min_dist_to_empty = math.inf
        for position in empty_development_positions:
            dist = position.distance_to(target)
            if dist < min_dist_to_empty:
                min_dist_to_empty = dist
        positions_scores[target] = 100 - min_dist_to_empty - 10 * (cluster.cell_infos[target].my_city_tile is not None)

    moves_solutions, scores = solve_churn_with_score(positions_options, positions_scores)
    moves, source_to_list = get_move_actions_with_blocks(positions_options, moves_solutions, cluster)
    actions += moves
    for source, towards in source_to_list:
        units_on_resource.remove(source)
        if towards in cluster.resource_positions:
            units_on_resource.append(towards)

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
                    blocked_empty_tiles.remove(unit_pos)
                # Treat as pushed even if could not act. Otherwise another unit would be pushed out of city to fulfill this.
                push_out_units_remaining -= 1
                push_out_units.remove(unit_pos)
                satisfied_export_positions.add(export_pos)
                break

    # If units remain to be exported, generate moves from cities towards push-out positions next to unsatisfied exports.
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
            adjacent_mining_positions = [p for p in get_adjacent_mining_positions(cluster, cell_pos) if
                                         not cluster.cell_infos[p].my_city_tile and
                                         not cluster.cell_infos[p].opponent_city_tile]
            free_adj_mining_positions = [p for p in adjacent_mining_positions if
                                         p not in units_on_resource and
                                         p not in cannot_act_units and
                                         p not in blocked_empty_tiles]
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

    actions_allowance = [actions, remaining_new_units_allowance]
    return actions_allowance


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
                move_solutions_reduction, score = solve_churn_with_score(positions_options_reduction,
                                                                         positions_scores)
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


# TODO: account for research level.
def get_adjacent_mining_positions(cluster: Cluster, p: Position):
    adjacent_mining_positions = []
    for cell_pos, cell_info in cluster.cell_infos.items():
        if not p.is_adjacent(cell_pos):
            continue
        if cell_info.mining_potential['WOOD'] > 0:
            adjacent_mining_positions.append(cell_pos)
    return adjacent_mining_positions


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


def get_units_needed(c: Cluster):
    serviceable_positions = 0
    has_units_count = 0
    for pos, cell_info in c.cell_infos.items():
        if cell_info.my_units:
            has_units_count += len(cell_info.my_units)
        if cell_info.my_city_tile or cell_info.resource:
            serviceable_positions += 1
    optimal_units_count = serviceable_positions / 6
    return optimal_units_count, has_units_count
