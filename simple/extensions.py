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
            if not is_empty(x, y, game_state):
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

def get_adjacent_positions(pos: Position, game_state: Game):
    #Todo


def get_adjacent_resource(unit: Unit, game_state: Game) -> Optional[Position]:
    for x in range(max(unit.pos.x - 1, 0), min(unit.pos.x + 2, game_state.map_width)):
        for y in range(max(unit.pos.y - 1, 0), min(unit.pos.y + 2, game_state.map_height)):
            # Exclude diagonally adjacent
            if unit.pos.x != x and unit.pos.y != y:
                continue
            if game_state.map.get_cell(x, y).has_resource():
                return Position(x, y)
    return None

def get_adjacent_empty(pos: Position, game_state: Game):
    for x in range(max(0, pos.x - 1), min(game_state.map_width, pos.x + 2)):
        for y in range(max(0, pos.y - 1), min(game_state.map_height, pos.y + 2)):
            current_cell = game_state.map.get_cell(x, y)
            if current_cell.has_resource() or current_cell.citytile is not None:
                continue
            else:
                return Position(x, y)
    return None

def get_adjacent_city(pos: Position, game_state: Game):
    for x in range(max(0, pos.x - 1), min(game_state.map_width, pos.x + 2)):
        for y in range(max(0, pos.y - 1), min(game_state.map_height, pos.y + 2)):
            current_cell = game_state.map.get_cell(x, y)

def get_shortest_way_to_city(unit: Unit, city: City):
    min_distance = math.inf
    min_distance_pos = None
    for tile in city.citytiles:
        distance = tile.pos.distance_to(unit.pos)
        if distance < min_distance:
            min_distance = distance
            min_distance_pos = tile.pos
    return min_distance, min_distance_pos



def is_empty(x, y, game_state):
    is_empty(Position(x,y), game_state)

def is_empty(pos: Position, game_state: Game):
    cell = game_state.map.get_cell_by_pos(pos)
    return not (cell.has_resource() or cell.citytile is not None)


def is_city_expandable(city: City, game_state: Game) -> bool:
    for tile in city.citytiles:
        if get_adjacent_empty(tile.pos, game_state) is not None:
            return True
    return False
