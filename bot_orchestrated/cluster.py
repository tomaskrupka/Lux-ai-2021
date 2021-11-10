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
                 turn: int,
                 units_build_allowance: int,
                 units_export_positions: list,
                 units_export_count: int,
                 upcoming_cycles: list,
                 research_level: int,
                 width: int):
        self.turn = turn
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
        all_adjacent_positions = extensions.get_adjacent_positions_cluster(non_empty_coordinates, game_state.map_width)

        all_cluster_coordinates = all_adjacent_positions.union(non_empty_coordinates)
        # positions adjacent to the core resources and my cities
        self.perimeter = [pos for pos in all_cluster_coordinates if pos not in non_empty_coordinates]
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
        self.development_positions = [p for p in self.perimeter if self.cell_infos[p].is_empty]
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

