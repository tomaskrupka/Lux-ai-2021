import math

from lux import game_constants
from lux.game import Game
from lux.game_map import Position
from lux.game_objects import City


def get_adjacent_positions(p: Position, w):
    return [
        Position(a, b)
        for (a, b) in [(p.x - 1, p.y), (p.x + 1, p.y), (p.x, p.y - 1), (p.x, p.y + 1)]
        if (0 <= a < w and 0 <= b < w)
    ]


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
    if direction == "s":
        return Position(position.x, position.y + 1)
    if direction == "w":
        return Position(position.x - 1, position.y)
    if direction == "n":
        return Position(position.x, position.y - 1)
    if direction == "e":
        return Position(position.x + 1, position.y)
    if direction == "c":
        return position


def get_directions_to_target(position_from, position_to):
    x_diff = position_to.x - position_from.x
    y_diff = position_to.y - position_from.y
    if x_diff > 0:
        return "e"
    if x_diff < 0:
        return "w"
    if y_diff > 0:
        return "s"
    if y_diff < 0:
        return "n"
    return "c"


def get_all_directions_to_target(position_from, position_to):
    x_diff = position_to.x - position_from.x
    y_diff = position_to.y - position_from.y
    directions = []
    if x_diff > 0:
        directions.append(("e", x_diff))
    if x_diff < 0:
        directions.append(("w", -x_diff))
    if y_diff > 0:
        directions.append(("s", y_diff))
    if y_diff < 0:
        directions.append(("n", -y_diff))
    if not directions:
        directions.append(("c", 0))
    directions.sort(key=lambda x: x[1], reverse=True)
    return [d[0] for d in directions]


def get_days_to_night(turn):
    return max(30 - turn % 40, 0)


def get_mined_resource(research_level):
    mined_resource = "WOOD"
    if research_level >= 50:
        mined_resource = "COAL"
    if research_level >= 200:
        mined_resource = "URANIUM"
    return mined_resource


def get_mined_resource_for_cluster_development(research_level, turn, cities_count):
    mined_resource = "WOOD"
    next_night_research_level = (
        research_level
        + get_days_to_night(turn)
        * cities_count
        / game_constants.GAME_CONSTANTS["BOT_SETTINGS"]["CITY_RESEARCH_PERIOD_TURNS"]
    )
    if next_night_research_level >= 50:
        mined_resource = "COAL"
    if next_night_research_level >= 200:
        mined_resource = "URANIUM"
    return mined_resource


def get_unit_range(cargo, turn):
    days_to_night = get_days_to_night(turn)
    return int((days_to_night + cargo / 4) / 2)


def get_distance_position_to_cluster(position, cluster):
    min_distance = math.inf
    min_distance_pos = None
    for perimeter_pos in cluster.perimeter:
        distance = perimeter_pos.distance_to(position)
        if min_distance > distance:
            min_distance = distance
            min_distance_pos = perimeter_pos
    return min_distance, min_distance_pos


def get_nights_remaining(turn):
    this_turn_remaining_nights = min(10, 40 - (turn % 40))
    turns_remaining = int((360 - turn) / 40)
    return this_turn_remaining_nights + 10 * turns_remaining


def get_fuel_remaining_to_survival(city: City, turn):
    return city.get_light_upkeep() * get_nights_remaining(turn) - city.fuel
