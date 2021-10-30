from typing import NamedTuple

from bot_orchestrated import extensions
from lux.game import Game
from lux.game_constants import GAME_CONSTANTS
from lux.game_map import Resource
from lux.game_objects import Player, CityTile, City


class CellInfo:
    def __init__(
            self,
            x: int,
            y: int,
            is_empty: bool,
            my_city_tile: CityTile,
            opponent_city_tile: CityTile,
            my_city: City,
            opponent_city: City,
            resource: Resource,
            my_units: list,
            opponent_units: list):
        self.mining_potential = None
        self.x = x
        self.y = y
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
        self.resource_xys = set()

        adjacent_coordinates = extensions.get_adjacent_positions_cluster(non_empty_coordinates, game_state.map_width)
        all_cluster_coordinates = adjacent_coordinates.union(non_empty_coordinates)
        for (x, y) in all_cluster_coordinates:

            cell_info = game_state.map.get_cell(x, y)
            my_city_tile = my_city_tiles[(x, y)][1] if (x, y) in my_city_tiles else None
            opponent_city_tile = opponent_city_tiles[(x, y)][1] if (x, y) in opponent_city_tiles else None
            has_resource = cell_info.has_resource()
            if has_resource:
                self.resource_xys.add((x, y))
            cell_info = CellInfo(
                x=x,
                y=y,
                my_city_tile=my_city_tile,
                opponent_city_tile=opponent_city_tile,
                my_city=my_city_tiles[(x, y)][0] if my_city_tile is not None else None,
                opponent_city=opponent_city_tiles[(x, y)][0] if opponent_city_tile is not None else None,
                resource=cell_info.resource,
                is_empty=my_city_tile is None and opponent_city_tile is None and not has_resource,
                my_units=my_units[(x, y)] if (x, y) in my_units else [],
                opponent_units=opponent_units[(x, y)] if (x, y) in opponent_units else []
            )
            self.cell_infos[(x, y)] = cell_info

        for cell_coords in self.cell_infos:
            resource_amounts = dict(WOOD=0, COAL=0, URANIUM=0)
            for xy in extensions.get_adjacent_positions(cell_coords[0], cell_coords[1], game_state.map_width) + [cell_coords]:
                if xy in self.cell_infos:
                    cell_info = self.cell_infos[xy]
                    if cell_info.resource is None:
                        continue
                    else:
                        for RESOURCE_TYPE, resource_type in GAME_CONSTANTS['RESOURCE_TYPES'].items():
                            if cell_info.resource.type == resource_type:
                                amount = cell_info.resource.amount
                                collection_rate = GAME_CONSTANTS['PARAMETERS']['WORKER_COLLECTION_RATE'][RESOURCE_TYPE]
                                resource_amounts[RESOURCE_TYPE] += amount if amount < collection_rate else collection_rate
                                break
            self.cell_infos[cell_coords].mining_potential = resource_amounts




def develop_cluster(cluster: Cluster, cluster_development_settings: ClusterDevelopmentSettings):
    taken_moves = set()

    unit_cell: CellInfo
    for unit_cell in [cell_info for cell_coords, cell_info in cluster.cell_infos if len(cell_info.my_units) > 0]:
        # worker(s) in city? Go in.
        if unit_cell.my_city_tile is not None:
            pass

    unit_build_allowance_remaining = cluster_development_settings.units_build_allowance
    for city_cell in [cell_info for cell_coords, cell_info in cluster.cell_infos if cell_info.my_city_tile is not None]:
        if city_cell.my_city_tile.can_act():
            if unit_build_allowance_remaining > 0:
                city_cell.my_city_tile.build_worker()
                unit_build_allowance_remaining -= 1
            else:
                city_cell.my_city_tile.research()
