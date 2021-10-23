import extensions
from lux.game import Game
from lux.game_objects import City, Unit


def step_towards_city(unit, city):
    min_distance, min_distance_pos = extensions.get_shortest_way_to_city(unit, city)
    return unit.move(unit.pos.direction_to(min_distance_pos))


def return_to_city(unit: Unit, city: City, game_state: Game):

    # Are you next to a city?
    if extensions.get_distance(unit.pos, city) == 1:

        # Yes: Will the city survive night if expanded? Rough upper estimate
        city_survives_if_expanded = city.fuel >= city.get_light_upkeep() * 10 + 18
        if city_survives_if_expanded:

            # Yes: Are you on an empty tile?
            if extensions.is_empty(unit.pos, game_state):

                # Yes: build city tile.
                return unit.build_city()

            else:

                # No: step into city.
                return step_towards_city(unit, city)

        else:

            # No: step into city.
            return step_towards_city(unit, city)
    else:

        # No: step towards city.
        return step_towards_city(unit, city)


