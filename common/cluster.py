from lux.game_map import Position
import extensions
from lux.game import Game


def get_clusters(game_state: Game):
    clusters = []
    coordinates_lists = detect_clusters_coordinates(game_state)
    for cluster_id, coordinates_list in coordinates_lists.items():
        clusters.append(Cluster(coordinates_list, game_state))
    return clusters


def detect_clusters_coordinates(game_state: Game):
    clusters = dict()
    cluster_ids_to_remove = set()
    last_cluster_id = -1
    for x in range(game_state.map_width):
        for y in range(game_state.map_height):
            if game_state.map.get_cell(x, y).has_resource():
                this_cell_cluster = None
                for cluster_id, cluster in clusters.items():
                    if cluster_id in cluster_ids_to_remove:
                        continue
                    if belongs_to_cluster(x, y, cluster, game_state):
                        if this_cell_cluster is None:
                            this_cell_cluster = cluster
                            cluster.append((x, y))
                        else:
                            cluster_ids_to_remove.add(cluster_id)
                            for cell in cluster:
                                this_cell_cluster.append(cell)
                if this_cell_cluster is None:
                    last_cluster_id += 1
                    clusters[last_cluster_id] = [(x, y)]
    for cluster_id in cluster_ids_to_remove:
        clusters.pop(cluster_id)
    return clusters


def belongs_to_cluster(x, y, cluster, game_state):
    pos_resource_type = game_state.map.get_cell(x, y).resource.type
    (a, b) = cluster[0]
    cluster_resource_type = game_state.map.get_cell(a, b).resource.type
    if pos_resource_type != cluster_resource_type:
        return False
    for (a, b) in cluster:
        if (a == x and abs(b - y) == 1) or ((b == y) and abs(a - x) == 1) or ((abs(b - y) == 1) and (abs(a - x) == 1)):
            return True
    return False


class Cluster:

    def __init__(self, coordinates_list, game_state):
        self.positions = []
        self.mining_positions = set()
        self.resource_type = game_state.map.get_cell(coordinates_list[0][0], coordinates_list[0][1]).resource.type
        for (a, b) in coordinates_list:
            self.positions.append(Position(a, b))
            for adjacent_position in extensions.get_adjacent_positions(a, b, game_state.map_width):
                self.mining_positions.add(adjacent_position)

    def is_all_access_points_secured(self):
        pass

    def is_self_sustainable(self):
        pass

    def get_empty_adjacent_positions(self, game_state: Game):
        mining_positions = set()
        for position in self.positions:
            adjacent_positions = extensions.get_adjacent_positions(position.x, position.y, game_state.map_width)
            for adj_position in adjacent_positions:
                if extensions.is_empty(adj_position, game_state):
                    mining_positions.add((position.x, position.y))
        return mining_positions
