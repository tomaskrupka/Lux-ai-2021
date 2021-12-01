import extensions
import develop_cluster
import cluster
from lux import game_constants
from lux.game import Game
from lux.game_objects import Unit


def send_free_units_to_empty_clusters(
        free_units_positions,
        scores_clusters,
        my_units_dict,
        turn,
        blocked_positions,
        cannot_act_units_ids):
    a = []
    b = []
    c = []
    not_moved_units_positions = set(free_units_positions)
    clusters_ids_units = dict()  # cluster_id = count of units going there
    for score, free_cluster in scores_clusters:
        clusters_ids_units[free_cluster.cluster_id] = game_constants.GAME_CONSTANTS["BOT_SETTINGS"]["MAX_FREE_UNITS_PER_CLUSTER"]

    for free_unit_position in free_units_positions:
        unit: Unit
        unit = my_units_dict[free_unit_position][0]
        max_units_per_cluster = min(clusters_ids_units.values()) + 2
        if unit.id not in cannot_act_units_ids:
            # choose the highest ranking free_cluster that you can make it to.
            for score, free_cluster in scores_clusters:
                if max_units_per_cluster > clusters_ids_units[free_cluster.cluster_id]:
                    distance, perimeter_position = extensions.get_distance_position_to_cluster(free_unit_position, free_cluster)
                    unit_range = extensions.get_unit_range(100 - unit.get_cargo_space_left(), turn)
                    if distance < unit_range:
                        directions = extensions.get_all_directions_to_target(free_unit_position, perimeter_position)
                        free_directions = []
                        for direction in directions:
                            new_pos = extensions.get_new_position(free_unit_position, direction)
                            if new_pos not in blocked_positions and new_pos not in b:
                                free_directions.append((direction, new_pos))
                        if free_directions:
                            direction = free_directions[0] # if len(free_directions) == 1 else free_directions[turn % 2]
                            a.append(unit.move(direction[0]))
                            b.append(direction[1])
                            c.append(unit.id)
                            not_moved_units_positions.remove(free_unit_position)
                            clusters_ids_units[free_cluster.cluster_id] += 1
                            break
    return a, b, c, not_moved_units_positions, clusters_ids_units


def send_units_to_closest_cluster(units_positions, clusters, my_units_dict, blocked_positions, cannot_act_units, turn):
    a = []
    b = []
    c = []
    not_moved_units_positions = set(units_positions)
    for pos in units_positions:
        unit = my_units_dict[pos][0]
        if unit.id not in cannot_act_units:
            closest_cluster_dist = 100
            target_pos = None
            for any_cluster in clusters:
                distance, perimeter_position = extensions.get_distance_position_to_cluster(pos, any_cluster)
                if distance < closest_cluster_dist:
                    target_pos = perimeter_position
                    closest_cluster_dist = distance
            directions = extensions.get_all_directions_to_target(pos, target_pos)
            if target_pos is not None:
                free_directions = []
                for direction in directions:
                    new_pos = extensions.get_new_position(pos, direction)
                    if new_pos not in blocked_positions and new_pos not in b:
                        free_directions.append((direction, new_pos))
                if free_directions:
                    direction = free_directions[0] # if len(free_directions) == 1 else free_directions[turn % 2]
                    a.append(unit.move(direction[0]))
                    b.append(direction[1])
                    c.append(unit.id)
                    not_moved_units_positions.remove(pos)
    return a, b, c, not_moved_units_positions


def develop_clusters(
        developing_clusters,
        developing_clusters_requirements,
        remaining_units_allowance,
        research_level,
        game_state: Game):
    a = []
    r = remaining_units_allowance
    researched = 0
    for developing_cluster in developing_clusters:
        export_positions = developing_clusters_requirements[developing_cluster.cluster_id]
        development_result = develop_cluster.develop_cluster(
            developing_cluster,
            cluster.ClusterDevelopmentSettings(
                turn=game_state.turn,
                units_build_allowance=r,
                units_export_positions=export_positions,
                research_level=research_level + researched,
                width=game_state.map_width),
            game_state)
        if 0 >= r != development_result[1]:
            print('fixme: units allowance changed when building was not permitted.')
        r = development_result[1]
        a += development_result[0]
        researched += development_result[2]
    return a, r

