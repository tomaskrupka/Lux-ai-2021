import math

import extensions
from lux.game_map import Position
from lux.game_objects import Player
from cluster import Cluster, CellInfo
from lux.game import Game


def get_player_city_tiles(player):
    player_city_tiles = dict()
    for k, city in player.cities.items():
        for tile in city.citytiles:
            player_city_tiles[tile.pos] = (city, tile)
    return player_city_tiles


def get_player_unit_tiles(player: Player):
    player_worker_tiles = dict()
    for unit in player.units:
        if unit.pos in player_worker_tiles:
            player_worker_tiles[unit.pos].append(unit)
        else:
            player_worker_tiles[unit.pos] = [unit]
    return player_worker_tiles


def detect_clusters(game_state, player, my_city_tiles, opponent_city_tiles, my_units, opponent_units):
    clusters = dict()
    coordinates_lists = detect_clusters_coordinates(game_state, my_city_tiles)
    for cluster_id, coordinates_list in coordinates_lists.items():
        clusters[cluster_id] = Cluster(cluster_id, coordinates_list, game_state, my_city_tiles, opponent_city_tiles, my_units, opponent_units)
    return clusters


def detect_clusters_coordinates(game_state: Game, player_city_tiles):
    clusters = dict()
    cluster_ids_to_remove = set()
    last_cluster_id = -1
    for x in range(game_state.map_width):
        for y in range(game_state.map_height):
            p = Position(x, y)
            cell = game_state.map.get_cell(x, y)
            if cell.has_resource() or (p in player_city_tiles):
                cell_cluster = None
                for cluster_id, cluster in clusters.items():
                    if cluster_id in cluster_ids_to_remove:
                        continue
                    if _has_perimeter_overlap(x, y, cluster):
                        if cell_cluster is None:
                            cell_cluster = cluster
                            cluster.append(Position(x, y))
                        else:
                            cluster_ids_to_remove.add(cluster_id)
                            for xy in cluster:
                                cell_cluster.append(xy)
                if cell_cluster is None:
                    last_cluster_id += 1
                    clusters[last_cluster_id] = [Position(x, y)]
    for cluster_id in cluster_ids_to_remove:
        clusters.pop(cluster_id)
    return clusters


def _has_perimeter_overlap(x, y, cluster):
    for p in cluster:
        if (p.x == x and abs(p.y - y) <= 2) or ((p.y == y) and abs(p.x - x) <= 2) or (
                (abs(p.y - y) == 1) and (abs(p.x - x) == 1)):
            return True
    return False


def get_closest_cluster(position: Position, clusters: [Cluster]):
    min_distance_cluster = None
    min_distance_pos = None
    min_distance = math.inf
    for c in clusters:
        for pos in c.cell_infos:
            dist = pos.distance_to(position)
            if dist < min_distance:
                min_distance = dist
                min_distance_cluster = c
                min_distance_pos = pos
    return min_distance_cluster, min_distance_pos


def get_cluster_export_positions_for_free_cluster(free_cluster: Cluster, exporting_cluster: Cluster, w):
    cluster_export_positions = get_cluster_export_positions(exporting_cluster, w)
    export_positions_scores = []
    for export_position in cluster_export_positions:
        min_distance = math.inf
        for pos in free_cluster.cell_infos:
            distance = pos.distance_to(export_position)
            if distance < min_distance:
                min_distance = distance
        export_positions_scores.append((export_position, min_distance))
    export_positions_scores.sort(key=lambda x: x[1])
    return export_positions_scores


def get_cluster_export_positions(cluster: Cluster, w):
    export_positions = set()
    for pos in cluster.cell_infos:
        for adj_pos in extensions.get_adjacent_positions(pos, w):
            if adj_pos not in cluster.cell_infos:
                export_positions.add(adj_pos)
    return export_positions
