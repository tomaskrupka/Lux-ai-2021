import math
from typing import NamedTuple
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


class ClusterDevelopmentSettings(NamedTuple):
    units_build_allowance: int


class Cluster:

    def __init__(self, non_empty_coordinates, game_state: Game, my_city_tiles, opponent_city_tiles, my_units,
                 opponent_units):
        self.cell_infos = dict()
        self.resource_positions = set()
        adjacent_positions = extensions.get_adjacent_positions_cluster(non_empty_coordinates, game_state.map_width)

        all_cluster_coordinates = adjacent_positions.union(non_empty_coordinates)
        self.development_positions = [pos for pos in all_cluster_coordinates if pos not in non_empty_coordinates]
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
    remaining_units_allowance = cluster_development_settings.units_build_allowance
    city_cell: CellInfo
    for city_cell in [cell_info for cell_coords, cell_info in cluster.cell_infos.items() if
                      cell_info.my_city_tile is not None]:
        if city_cell.my_city_tile.can_act():
            if remaining_units_allowance > 0:
                actions.append(city_cell.my_city_tile.build_worker())
                remaining_units_allowance -= 1
            else:
                actions.append(city_cell.my_city_tile.research())

    # build city tiles
    # TODO: exclude units coming to the city with resources.
    blocked_empty_tiles = []
    for cell_pos, cell_info in cluster.cell_infos.items():
        if cell_info.is_empty and len(cell_info.my_units) > 0:
            unit = cell_info.my_units[0]
            blocked_empty_tiles.append(cell_pos)
            if unit.can_act() and unit.get_cargo_space_left() == 0:
                actions.append(unit.build_city())

    # step out of resource tiles where adjacent empty
    positions_options = []
    blocked_units_on_resource = []
    cannot_act_units_on_resource = []
    can_act_units_on_resource = []
    for cell_pos, cell_info in cluster.cell_infos.items():
        if cell_info.resource is not None and len(cell_info.my_units) > 0:
            if cell_info.my_units[0].can_act():
                can_act_units_on_resource.append(cell_pos)
            else:
                cannot_act_units_on_resource.append(cell_pos)
    for pos in can_act_units_on_resource:
        adjacent_development_positions = get_adjacent_development_positions(cluster, pos)
        if len(adjacent_development_positions) > 0:
            positions_options.append([pos, [p for p in adjacent_development_positions if p not in cannot_act_units_on_resource and p not in blocked_empty_tiles]])
        else:
            # had no adjacent development position
            blocked_units_on_resource.append(pos)
    moves_solutions = solve_churn(positions_options)
    moves, blocked_positions = get_move_actions(moves_solutions, cluster)
    actions += moves
    for blocked_pos in blocked_positions:
        # had some adjacent development positions, but others took them
        blocked_units_on_resource.append(blocked_pos)

    # take a step towards empty where no adjacent empty

    # step out of cities into mining positions
    positions_options = []
    for cell_pos, cell_info in cluster.cell_infos.items():
        if cell_info.my_city_tile is not None and len(cell_info.my_units) > 0:
            adjacent_mining_positions = get_adjacent_mining_positions(cluster, cell_pos)
            free_adj_mining_positions = [p for p in adjacent_mining_positions if p not in blocked_units_on_resource and p not in cannot_act_units_on_resource and p not in blocked_empty_tiles]
            if len(free_adj_mining_positions) > 0:
                positions_options.append([cell_pos, free_adj_mining_positions])
    moves_solutions = solve_churn(positions_options)
    moves, blocked_positions = get_move_actions(moves_solutions, cluster)
    actions += moves

    return actions, remaining_units_allowance


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


def get_adjacent_development_positions(cluster: Cluster, p: Position):
    adjacent_development_positions = []
    if p in cluster.development_positions:
        adjacent_development_positions.append(p)
    for q in cluster.development_positions:
        if (q.x == p.x and abs(q.y - p.y) == 1) or (q.y == p.y and abs(q.x - p.x) == 1):
            adjacent_development_positions.append(q)
    return adjacent_development_positions


# TODO: account for research level.
def get_adjacent_mining_positions(cluster: Cluster, p: Position):
    adjacent_mining_positions = []
    if cluster.cell_infos[p].mining_potential['WOOD'] > 0:
        adjacent_mining_positions.append(p)
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
