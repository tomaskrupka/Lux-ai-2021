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
            if not game_state.map.get_cell(x, y).has_resource():
                continue

            position = Position(x, y)
            distance = unit.pos.distance_to(position)
            if distance < distance_nearest_resource:
                distance_nearest_resource = distance
                position_nearest_resource = position
    return position_nearest_resource, distance_nearest_resource


def get_nearest_empty_tile(unit: Unit, game_state: Game) -> (Position, int):
    distance_nearest_empty = math.inf
    position_nearest_empty = None
    for x in range(game_state.map_width):
        for y in range(game_state.map_height):
            if not is_empty(Position(x, y), game_state):
                continue

            position = Position(x, y)
            distance = unit.pos.distance_to(position)
            if distance < distance_nearest_empty:
                distance_nearest_empty = distance
                position_nearest_empty = position
    return position_nearest_empty, distance_nearest_empty


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


def get_adjacent_positions(x, y, w):
    return [(a, b) for (a, b) in [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)] if (0 <= a < w and 0 <= b < w)]


def get_adjacent_resource(unit, game_state):
    for p in get_adjacent_positions(unit.pos.x, unit.pos.y, game_state.map_width):
        if game_state.map.get_cell(p[0], p[1]).has_resource():
            return Position(p[0], p[1])
    return None


def get_adjacent_empty(pos, game_state):
    for p in get_adjacent_positions(pos.x, pos.y, game_state.map_width):
        cell = game_state.map.get_cell(p[0], p[1])
        if cell.has_resource() or cell.citytile is not None:
            continue
        else:
            return Position(p[0], p[1])
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


def is_empty(pos: Position, game_state: Game):
    cell = game_state.map.get_cell_by_pos(pos)
    return not (cell.has_resource() or cell.citytile is not None)


def is_city_expandable(city: City, game_state: Game) -> bool:
    for tile in city.citytiles:
        if get_adjacent_empty(tile.pos, game_state) is not None:
            return True
    return False
