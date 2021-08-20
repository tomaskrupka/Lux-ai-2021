import math

from lux.game import Game
from lux.game_map import Position
from lux.game_objects import City


def get_distance(pos: Position, city: City) -> int:
    min_distance = math.inf
    for tile in city.citytiles:
        distance = tile.pos.distance_to(pos)
        if distance == 0:
            return 0
        elif distance < min_distance:
            min_distance = distance
    return distance


def get_nearest_adjacent_empty(pos: Position, city: City, game_state: Game) -> Position:
    min_distance_pos_adjacent = math.inf
    position = None
    for x in range(game_state.map_width):
        for y in range(game_state.map_height):
            map_position = Position(x, y)
            if get_distance(map_position, city) != 1:
                continue
            cell = game_state.map.get_cell(x, y)
            cell_is_empty = (not cell.has_resource()) & (cell.citytile is None)
            if not cell_is_empty:
                continue
            distance = pos.distance_to(map_position)
            # Found tile adjacent to the city that is closer to the position, save it.
            if distance < min_distance_pos_adjacent:
                min_distance_pos_adjacent = distance
                position = map_position
    return position


def can_survive_night(city: City):
    return city.fuel >= city.get_light_upkeep() * 10
