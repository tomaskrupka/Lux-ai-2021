from typing import NamedTuple

from bot_orchestrated import extensions
from lux.game import Game
from lux.game_objects import Player


class Cluster:

    def __init__(self, non_empty_coordinates, game_state: Game, player_city_tiles_xys, opponent_city_tiles_xys):
        self.cell_infos = []
        adjacent_coordinates = extensions.get_adjacent_positions_cluster(non_empty_coordinates, game_state.map_width)
        all_coordinates = adjacent_coordinates.union(non_empty_coordinates)
        for (x, y) in all_coordinates:
            cell = game_state.map.get_cell(x, y)
            is_my_city_tile = (x, y) in player_city_tiles_xys
            is_opponent_city_tile = (x, y) in opponent_city_tiles_xys
            has_resource = cell.has_resource()
            cell_info = CellInfo(
                x=x,
                y=y,
                is_my_city_tile=is_my_city_tile,
                is_opponent_city_tile=is_opponent_city_tile,
                has_resource=has_resource,
                is_empty=not is_my_city_tile and not is_opponent_city_tile and not has_resource,
                resource_type=cell.resource.type if has_resource else None,
                resource_amount=cell.resource.amount if has_resource else 0,
                my_units=[],
                opponent_units=[]
            )
            self.cell_infos.append(cell_info)
        print('done')


class CellInfo(NamedTuple):
    x: int
    y: int
    is_empty: bool
    is_my_city_tile: bool
    is_opponent_city_tile: bool
    has_resource: bool
    resource_type: str
    resource_amount: int
    my_units: list
    opponent_units: list
