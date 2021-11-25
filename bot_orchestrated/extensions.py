import math
from typing import Optional

from lux.game import Game
from lux.game_map import Position


def get_adjacent_positions(p: Position, w):
    return [Position(a, b) for (a, b) in [(p.x - 1, p.y), (p.x + 1, p.y), (p.x, p.y - 1), (p.x, p.y + 1)] if
            (0 <= a < w and 0 <= b < w)]


def get_adjacent_positions_cluster(coordinates, w):
    adjacent_positions = set()
    for position in coordinates:
        for adjacent_position in get_adjacent_positions(position, w):
            adjacent_positions.add(adjacent_position)
    return adjacent_positions


# Adjacent positions minus opponent cities
def get_possible_moves(unit, game_state: Game):
    possible_moves = []
    for p in get_adjacent_positions(unit.pos, game_state.map_width):
        city_tile = game_state.map.get_cell_by_pos(p).citytile
        if city_tile is None or city_tile.team == unit.team:
            possible_moves.append(p)
    return possible_moves


def get_new_position(position, direction):
    if direction == 's':
        return Position(position.x, position.y + 1)
    if direction == 'w':
        return Position(position.x - 1, position.y)
    if direction == 'n':
        return Position(position.x, position.y - 1)
    if direction == 'e':
        return Position(position.x + 1, position.y)
    if direction == 'c':
        return position


def get_directions_to_target(position_from, position_to):
    x_diff = position_to.x - position_from.x
    y_diff = position_to.y - position_from.y
    if x_diff > 0:
        return 'e'
    if x_diff < 0:
        return 'w'
    if y_diff > 0:
        return 's'
    if y_diff < 0:
        return 'n'
    return 'c'


def get_all_directions_to_target(position_from, position_to):
    x_diff = position_to.x - position_from.x
    y_diff = position_to.y - position_from.y
    directions = []
    if x_diff > 0:
        directions.append('e')
    if x_diff < 0:
        directions.append('w')
    if y_diff > 0:
        directions.append('s')
    if y_diff < 0:
        directions.append('n')
    if not directions:
        directions.append('c')
    return directions


def get_days_to_night(turn):
    return max(30 - turn % 40, 0)
