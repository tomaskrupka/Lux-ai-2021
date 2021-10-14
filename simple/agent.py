
import cluster
import actions
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

    clusters = cluster.get_clusters(game_state)

    taken_moves = set()

    player = game_state.players[observation.player]

    max_resource_type = "wood"

    if player.research_points >= 50:
        max_resource_type = "coal"

    if player.research_points >= 200:
        max_resource_type = "uranium"

    opponent = game_state.players[(observation.player + 1) % 2]
    width, height = game_state.map.width, game_state.map.height

    resource_tiles: list[Cell] = []
    for y in range(height):
        for x in range(width):
            cell = game_state.map.get_cell(x, y)
            if cell.has_resource():
                resource_tiles.append(cell)

    owned_city_tiles = sum(len(city.citytiles) for k, city in player.cities.items())
    owned_units = len(player.units)

    # Cities
    for k, city in player.cities.items():
        for city_tile in city.citytiles:
            if city_tile.can_act():
                if owned_units < owned_city_tiles:
                    actions.append(city_tile.build_worker())
                    owned_units += 1
                else:
                    actions.append(city_tile.research())

    # Units
    for worker in [unit for unit in player.units if unit.is_worker() and unit.can_act()]:

        # Are you in a city?
        city_worker_in = next((city for k, city in player.cities.items() if
                               any(tile for tile in city.citytiles if tile.pos.equals(worker.pos))), None)

        if city_worker_in is not None:

            # Yes: Is any resource adjacent to the city?
            nearest_adjacent_resource = extensions.get_nearest_adjacent_resource(worker.pos, city_worker_in, game_state, max_resource_type)
            if nearest_adjacent_resource is None:

                # No: Will you survive going to the nearest resource?
                nearest_resource_pos, nearest_resource_dist = extensions.get_nearest_resource(worker, game_state, max_resource_type)
                days_to_night = 30 - (game_state.turn % 40)
                can_reach_resource = nearest_resource_dist * 2 < days_to_night
                if can_reach_resource:
                    # Yes: Quest: Go mining
                    # Are you next to a resource? No as in a city that's not next to a resource.
                    nearest_resource_dir = worker.pos.direction_to(nearest_resource_pos)
                    new_position = extensions.get_new_position(worker.pos, nearest_resource_dir)

                    if (new_position.x, new_position.y) not in taken_moves:
                        taken_moves.add((new_position.x, new_position.y))
                        actions.append(worker.move(nearest_resource_dir))

        else:

            # No: Do you have free capacity?
            has_free_capacity = worker.get_cargo_space_left() > 0

            if has_free_capacity:

                # Yes: Go mining:
                # Are you next to a resource?

                adjacent_resource_position = extensions.get_adjacent_resource(worker, game_state, max_resource_type)
                if adjacent_resource_position is None:

                    # No: Find a way towards resource

                    possible_moves = extensions.get_possible_moves(worker, game_state)

                    for possible_move in possible_moves:
                        pass

                    nearest_resource_pos, nearest_resource_dist = extensions.get_nearest_resource(worker, game_state, max_resource_type)
                    nearest_resource_dir = worker.pos.direction_to(nearest_resource_pos)
                    new_position = extensions.get_new_position(worker.pos, nearest_resource_dir)

                    if (new_position.x, new_position.y) not in taken_moves:
                        taken_moves.add((new_position.x, new_position.y))
                        actions.append(worker.move(nearest_resource_dir))

                # else:

            else:

                # No: Are there any surviving cities?
                if len(player.cities) == 0:

                    # No: Start a new city.
                    actions.append(worker.build_city())
                else:

                    # Yes: Is any city low on fuel?
                    not_surviving_city = next(
                        (city for k, city in player.cities.items() if not extensions.can_city_survive_night(city)),
                        None)
                    if not_surviving_city is None:

                        actions.append(annotate.sidetext('surviving'))
                        # No: Can any city be expanded?
                        expandable_city = next(
                            (city for k, city in player.cities.items() if
                             extensions.is_city_expandable(city, game_state)), None)
                        if expandable_city is None:

                            # No: Start a city. Are you next to a resource?
                            if extensions.get_adjacent_resource(worker, game_state, max_resource_type) is None:

                                # No: Find a way towards resource, go there.
                                pos_res, dist_res = extensions.get_nearest_resource(worker, game_state, max_resource_type)
                                direction_nearest_resource = worker.pos.direction_to(pos_res)
                                new_position = extensions.get_new_position(worker.pos, direction_nearest_resource)

                                if (new_position.x, new_position.y) not in taken_moves:
                                    taken_moves.add((new_position.x, new_position.y))
                                    actions.append(worker.move(direction_nearest_resource))
                            else:

                                # Yes: Are you on an empty tile?
                                worker_on_empty_tile = extensions.is_empty(worker.pos, game_state)

                                if worker_on_empty_tile:

                                    # Yes: Build city tile
                                    actions.append(worker.build_city())

                                else:
                                    # No: Find a way towards empty tile
                                    position_nearest_empty, distance_nearest_empty = extensions.get_nearest_empty_tile(
                                        worker, game_state)
                                    direction_nearest_empty = worker.pos.direction_to(position_nearest_empty)

                                    new_position = extensions.get_new_position(worker.pos, direction_nearest_empty)

                                    if (new_position.x, new_position.y) not in taken_moves:
                                        taken_moves.add((new_position.x, new_position.y))
                                        actions.append(worker.move(direction_nearest_empty))

                        else:
                            # Yes: Return to expandable city
                            actions.append(annotate.sidetext('expandable'))
                            actions.append(actions.return_to_city(worker, expandable_city, game_state))

                    else:
                        # Yes: Return to city low on fuel
                        actions.append(actions.return_to_city(worker, not_surviving_city, game_state))
                        min_distance, min_distance_pos = extensions.get_shortest_way_to_city(worker, not_surviving_city)
                        direction_low_fuel_city = worker.pos.direction_to(min_distance_pos)

                        new_position = extensions.get_new_position(worker.pos, direction_low_fuel_city)

                        if (new_position.x, new_position.y) not in taken_moves:
                            taken_moves.add((new_position.x, new_position.y))
                            actions.append(worker.move(direction_low_fuel_city))

    # you can add debug annotations using the functions in the annotate object
    # actions.append(annotate.circle(0, 0))

    return actions
