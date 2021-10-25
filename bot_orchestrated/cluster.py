from lux.game import Game


def detect_clusters(game_state: Game, my_city_tiles):
    clusters = []
    coordinates_lists = detect_clusters_coordinates(game_state, my_city_tiles)
    for cluster_id, coordinates_list in coordinates_lists.items():
        clusters.append(Cluster(coordinates_list))
    return clusters


def detect_clusters_coordinates(game_state: Game, my_city_tiles_xy):
    clusters = dict()
    cluster_ids_to_remove = set()
    last_cluster_id = -1
    for x in range(game_state.map_width):
        for y in range(game_state.map_height):
            cell = game_state.map.get_cell(x, y)
            if cell.has_resource() or ((x, y) in my_city_tiles_xy):
                cell_cluster = None
                for cluster_id, cluster in clusters.items():
                    if cluster_id in cluster_ids_to_remove:
                        continue
                    if _has_perimeter_overlap(x, y, cluster):
                        if cell_cluster is None:
                            cell_cluster = cluster
                            cluster.append((x, y))
                        else:
                            cluster_ids_to_remove.add(cluster_id)
                            for cell in cluster:
                                cell_cluster.append(cell)
                if cell_cluster is None:
                    last_cluster_id += 1
                    clusters[last_cluster_id] = [(x, y)]
    for cluster_id in cluster_ids_to_remove:
        clusters.pop(cluster_id)
    return clusters


def _has_perimeter_overlap(x, y, cluster):
    for (a, b) in cluster:
        if (a == x and abs(b - y) <= 2) or ((b == y) and abs(a - x) <= 2) or ((abs(b - y) == 1) and (abs(a - x) == 1)):
            return True
    return False


class Cluster:
    coordinates = set()
    units = []
    cities = []

    def __init__(self, coordinates_list):
        self.coordinates = coordinates_list
