from lux.game_map import Position
import extensions
from lux.game import Game


# Todo: This merges clusters based on proximity (any common adjacent cell). Account for resource_type?

def detect_clusters(game_state: Game):
    clusters = [[]]
    clusters_to_remove = [[]]
    for x in range(game_state.map_width):
        for y in range(game_state.map_height):
            if game_state.map.get_cell(x, y).has_resource():
                this_cell_cluster = None
                for cluster in clusters:
                    if any(a for (a, b) in cluster if (a == x and abs(b - y) == 1) or ((b == y) and abs(a - x) == 1)):
                        if this_cell_cluster is None:
                            this_cell_cluster = cluster
                            cluster.append((x, y))
                        else:
                            # Cell has already been assigned to a cluster. Merging clusters
                            clusters_to_remove.append(cluster)
                            for cell in cluster:
                                this_cell_cluster.append(cell)

                if this_cell_cluster is None:
                    clusters.append([(x, y)])

    for cluster in clusters_to_remove:
        clusters.remove(cluster)

    return clusters


def detect_clusters_2(game_state: Game):
    clusters = dict()
    cluster_ids_to_remove = set()
    last_cluster_id = -1
    for x in range(game_state.map_width):
        for y in range(game_state.map_height):
            if game_state.map.get_cell(x, y).has_resource():
                this_cell_cluster = None
                for cluster_id, cluster in clusters.items():
                    if any(a for (a, b) in cluster if (a == x and abs(b - y) == 1) or ((b == y) and abs(a - x) == 1)):
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

class Cluster:
    def __init__(self, resource_type, positions):
        self.resource_type = resource_type
        self.positions = positions

    def get_empty_adjacent_positions(self, game_state: Game):
        mining_positions = set()
        for position in self.positions:
            adjacent_positions = extensions.get_adjacent_positions(position.x, position.y, game_state.map_width)
            for adj_position in adjacent_positions:
                if extensions.is_empty(adj_position):
                    mining_positions.add((position.x, position.y))
        return mining_positions
