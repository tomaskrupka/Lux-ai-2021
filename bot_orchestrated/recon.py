from lux.game_map import Position
from lux.game_objects import Player
from cluster import Cluster, CellInfo
from lux.game import Game


def get_free_units(game_state, clusters):
    for cluster in clusters:
        pass


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
    clusters = []
    coordinates_lists = detect_clusters_coordinates(game_state, my_city_tiles)
    for cluster_id, coordinates_list in coordinates_lists.items():
        clusters.append(Cluster(coordinates_list, game_state, my_city_tiles, opponent_city_tiles, my_units, opponent_units))
    return clusters


def detect_clusters_coordinates(game_state: Game, player_city_tiles):
    clusters = dict()
    cluster_ids_to_remove = set()
    last_cluster_id = -1
    for x in range(game_state.map_width):
        for y in range(game_state.map_height):
            p = Position(x,y)
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
        if (p.a == x and abs(p.b - y) <= 2) or ((p.b == y) and abs(p.a - x) <= 2) or ((abs(p.b - y) == 1) and (abs(p.a - x) == 1)):
            return True
    return False
