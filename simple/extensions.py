import math
from typing import Optional

from lux.game import Game
from lux.game_map import Position
from lux.game_objects import City, CityTile, Unit, Player


def get_distance(pos: Position, city: City) -> int:
    min_distance = math.inf
    for tile in city.citytiles:
        distance = tile.pos.distance_to(pos)
        if distance == 0:
            return 0
        elif distance < min_distance:
            min_distance = distance
    return min_distance


def get_nearest_adjacent_empty(pos: Position, city: City, game_state: Game) -> Position:
    min_distance_pos_adjacent = math.inf
    position = None
    for x in range(game_state.map_width):
        for y in range(game_state.map_height):
            map_position = Position(x, y)
            if get_distance(map_position, city) != 1:
                continue
            else:
                cell = game_state.map.get_cell(x, y)
                cell_is_empty = (not cell.has_resource()) and (cell.citytile is None)
                if not cell_is_empty:
                    continue
                distance = pos.distance_to(map_position)
                # Found tile adjacent to the city that is closer to the position, save it.
                if distance < min_distance_pos_adjacent:
                    min_distance_pos_adjacent = distance
                    position = map_position
    return position


def can_city_survive_night(city: City) -> bool:
    return city.fuel >= city.get_light_upkeep() * 10


def can_unit_survive_night(unit: Unit) -> bool:
    if unit.is_worker():
        return unit.get_cargo_space_left() <= 60
    else:
        return True


def get_nearest_resource(unit: Unit, game_state: Game) -> (Position, int):
    distance_nearest_resource = math.inf
    position_nearest_resource = None
    for x in range(game_state.map_width):
        for y in range(game_state.map_height):
            position = Position(x, y)
            distance = unit.pos.distance_to(position)
            if distance < distance_nearest_resource:
                distance_nearest_resource = distance
                position_nearest_resource = position
    return position_nearest_resource, distance_nearest_resource


# Gets position of a resource that is the nearest to input position and adjacent to input city.
def get_nearest_adjacent_resource(pos: Position, city: City, game_state: Game) -> Position:
    min_distance_pos_adjacent = math.inf
    position = None
    for x in range(game_state.map_width):
        for y in range(game_state.map_height):
            map_position = Position(x, y)
            if get_distance(map_position, city) != 1:
                continue
            else:
                cell = game_state.map.get_cell(x, y)
                if not cell.has_resource():
                    continue
                distance = pos.distance_to(map_position)

                # Found tile adjacent to the city that is closer to the position, save it.
                if distance < min_distance_pos_adjacent:
                    min_distance_pos_adjacent = distance
                    position = map_position
    return position


def is_unit_in_city(player: Player, unit: Unit) -> CityTile:
    for k, city in player.cities.items():
        for tile in city.citytiles:
            if unit.pos.equals(tile.pos):
                return tile


def get_adjacent_resource(unit: Unit, game_state: Game) -> Optional[Position]:
    for x in range(max(unit.pos.x - 1, 0), min(unit.pos.x + 1, game_state.map_width)):
        for y in range(max(unit.pos.y - 1, 0), min(unit.pos.y + 1, game_state.map_height)):
            if unit.pos.x == x and unit.pos.y == y:
                continue
            if game_state.map.get_cell(x, y).has_resource():
                return Position(x, y)
    return None


def get_shortest_way_to_city(unit: Unit, city: City):
    min_distance = math.inf
    min_distance_pos = None
    for tile in city.citytiles:
        distance = tile.pos.distance_to(unit.pos)
        if distance < min_distance:
            min_distance = distance
            min_distance_pos = tile.pos
    return min_distance, min_distance_pos
