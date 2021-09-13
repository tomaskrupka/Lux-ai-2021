import extensions
import math

if __package__ == "":
    # for kaggle-environments
    from lux.game import Game
    from lux.constants import Constants
    from lux import annotate

else:
    # for CLI tool
    from .lux.game import Game
    from .lux.game_map import Cell
    from .lux.constants import Constants
    from .lux import annotate

DIRECTIONS = Constants.DIRECTIONS
game_state = None


def agent(observation, configuration):
    global game_state

    ### Do not edit ###
    if observation["step"] == 0:
        game_state = Game()
        game_state._initialize(observation["updates"])
        game_state._update(observation["updates"][2:])
        game_state.id = observation.player
    else:
        game_state._update(observation["updates"])

    actions = []

    ### AI Code goes down here! ### 
    player = game_state.players[observation.player]
    opponent = game_state.players[(observation.player + 1) % 2]
    width, height = game_state.map.width, game_state.map.height

    resource_tiles: list[Cell] = []
    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell(x, y)
            if cell.has_resource():
                resource_tiles.append(cell)

    owned_city_tiles = sum(len(city.citytiles) for city in player.cities.values())
    owned_units = len(player.units)

    # Cities
    for k, city in player.cities.items():
        for city_tile in city.citytiles:
            if city_tile.can_act() and owned_units < owned_city_tiles:
                actions.append(city_tile.build_worker())
                owned_units += 1

    # Units
    for worker in [unit for unit in player.units if unit.is_worker() and unit.can_act()]:

        # Are you in a city?
        worker_in_city = any(city for k, city in player.cities.items() if
                             any(tile for tile in city.citytiles if tile.pos.equals(worker.pos)))
        actions.append(annotate.x(worker.pos.x, worker.pos.y))
        if worker_in_city:

            # Yes: Is any resource adjacent to the city?
            nearest_adjacent_resource = extensions.get_nearest_adjacent_resource(worker.pos, city, game_state)
            if nearest_adjacent_resource is None:

                # No: Will you survive going to the nearest resource?
                nearest_resource_pos, nearest_resource_dist = extensions.get_nearest_resource(worker, game_state)
                days_to_night = 30 - (game_state.turn % 40)
                can_reach_resource = nearest_resource_dist * 2 < days_to_night
                if can_reach_resource:

                    # Quest: Go mining
                    # Are you next to a resource? No as in a city that's not next to a resource.
                    nearest_resource_dir = worker.pos.direction_to(nearest_resource_pos)
                    actions.append(worker.move(nearest_resource_dir))

        else:

            # No: Do you have free capacity?
            has_free_capacity = worker.get_cargo_space_left() > 0
            if has_free_capacity:

                # Yes: Go mining:
                # Are you next to a resource?
                adjacent_resource_position = extensions.get_adjacent_resource(worker, game_state)
                if adjacent_resource_position is None:

                    # No: Find a way towards resource
                    nearest_resource_pos, nearest_resource_dist = extensions.get_nearest_resource(worker, game_state)
                    nearest_resource_dir = worker.pos.direction_to(nearest_resource_pos)
                    actions.append(worker.move(nearest_resource_dir))
            else:

                # No: Are there any surviving cities?
                if len(player.cities) == 0:

                    # No: Start a new city.
                    actions.append(worker.build_city())
                else:

                    # Yes: Is any city low on fuel?
                    not_surviving_city = next(city for k, city in player.cities.items() if not extensions.can_city_survive_night(city))
                    if not_surviving_city is None:

                        # No: Can any city be expanded?


                        # Yes: Return to the first city that's low on fuel.
                        min_distance, min_distance_pos = extensions.get_shortest_way_to_city(worker, city)





        closest_dist = math.inf
        closest_resource_tile = None
        if worker.get_cargo_space_left() > 0:
            for resource_tile in resource_tiles:
                if resource_tile.resource.type == Constants.RESOURCE_TYPES.COAL and not player.researched_coal():
                    continue
                if resource_tile.resource.type == Constants.RESOURCE_TYPES.URANIUM and not player.researched_uranium():
                    continue
                dist = resource_tile.pos.distance_to(worker.pos)
                if dist < closest_dist:
                    closest_dist = dist
                    closest_resource_tile = resource_tile
            if closest_resource_tile is not None:
                actions.append(worker.move(worker.pos.direction_to(closest_resource_tile.pos)))
        else:
            # if unit is a unity and there is no cargo space left, and we have cities, lets return to them
            if len(player.cities) > 0:
                closest_dist = math.inf
                closest_city_tile = None
                for k, city in player.cities.items():
                    for city_tile in city.citytiles:
                        dist = city_tile.pos.distance_to(worker.pos)
                        if dist < closest_dist:
                            closest_dist = dist
                            closest_city_tile = city_tile
                if closest_city_tile is not None:
                    city = player.cities[closest_city_tile.cityid]
                    # Expand the city.
                    if extensions.can_city_survive_night(city):
                        actions.append(annotate.sidetext('survives'))
                        target_position = extensions.get_nearest_adjacent_empty(worker.pos, city, game_state)
                        actions.append(annotate.line(worker.pos.x, worker.pos.y, target_position.x, target_position.y))
                        move_dir = worker.pos.direction_to(target_position)
                        if move_dir == DIRECTIONS.CENTER:
                            actions.append(worker.build_city())
                        else:
                            actions.append(worker.move(move_dir))
                    # Return to the city, not enough fuel in the city.
                    else:
                        actions.append(annotate.sidetext('dies'))
                        target_position = closest_city_tile.pos
                        move_dir = worker.pos.direction_to(target_position)
                        actions.append(worker.move(move_dir))
            else:
                actions.append(worker.build_city())

    # you can add debug annotations using the functions in the annotate object
    # actions.append(annotate.circle(0, 0))

    return actions
