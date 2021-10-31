import math
from typing import NamedTuple

from bot_orchestrated import extensions
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
        self.development_positions = extensions.get_adjacent_positions_cluster(non_empty_coordinates,
                                                                               game_state.map_width)
        all_cluster_coordinates = self.development_positions.union(non_empty_coordinates)
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
                city_cell.my_city_tile.build_worker()
            else:
                city_cell.my_city_tile.research()

    # build city tiles
    # TODO: exclude units coming to the city with resources.
    for cell_pos, cell_info in cluster.cell_infos.items():
        if cell_info.is_empty and len(cell_info.my_units) > 0:
            unit: Unit
            unit = cell_info.my_units[0]
            if unit.can_act() and unit.get_cargo_space_left() == 0:
                actions.append(unit.build_city())

    # step out of resource tiles
    move_options = []
    churn = dict()
    unmoved_units = []
    for cell_pos, cell_info in cluster.cell_infos.items():
        if cell_info.resource is not None and len(cell_info.my_units) > 0:
            adjacent_development_positions = get_adjacent_development_positions(cluster, cell_pos)
            if len(adjacent_development_positions) > 0:
                for adjacent_position in adjacent_development_positions:
                    churn[adjacent_position] = churn[adjacent_position] + 1 if adjacent_position in churn else 1
                move_options.append([cell_pos, adjacent_development_positions])
            else:
                unmoved_units.append(cell_pos)
    # prioritize units movements by how many options they have
    move_options.sort(key=lambda x: (len(x[1])))
    move_demands = list(churn.items())
    move_demands.sort(key=lambda x: (x[1]))
    blocked_moves = set()
    for cell_options in move_options:
        unit_coords = cell_options[0]
        unit_moves = cell_options[1]
        unit_moved = False
        for demand_option in move_demands:
            move_coords = demand_option[0]
            if move_coords in unit_moves and move_coords not in blocked_moves:
                blocked_moves.add(move_coords)
                unit = cluster.cell_infos[unit_coords].my_units[0]
                actions.append(unit.move(extensions.get_directions_to_target(Position(unit_coords[0], unit_coords[1]),
                                                                             Position(move_coords[0], move_coords[1]))))
                unit_moved = True
                break
        if not unit_moved:
            unmoved_units.append(unit_coords)


def get_adjacent_development_positions(cluster: Cluster, p: Position):
    adjacent_development_positions = []
    for q in cluster.development_positions:
        if (q.x == p.x and abs(q.y - p.y) == 1) or (q.y == p.y and abs(q.x - p.y) == 1):
            adjacent_development_positions.append(q)
    return adjacent_development_positions


def get_closest_development_position(cluster: Cluster, xy):
    min_dist = math.inf
    closest_position = None
    for (x, y) in cluster.development_positions:
        dist = abs(x - xy[0]) + abs(y - xy[1])
        if dist < min_dist:
            closest_position = (x, y)
            min_dist = dist
    return closest_position
