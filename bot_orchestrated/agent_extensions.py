import math

import extensions
from cluster import Cluster
import cluster_extensions as ce


def assign_clusters_for_export(developing_clusters, free_clusters, mined_resource, turn):
    free_cluster: Cluster
    developing_cluster: Cluster
    empty_unit_range = extensions.get_unit_range(0, turn)
    developing_clusters_export_requirements = dict()
    for developing_cluster in developing_clusters:
        developing_clusters_export_requirements[developing_cluster.cluster_id] = set()
    for free_cluster in free_clusters:
        min_dist = math.inf
        serving_cluster = None
        min_dist_sources = []
        for developing_cluster in developing_clusters:
            dist, sources = get_dist_sources_for_export(developing_cluster, free_cluster, mined_resource)
            if dist < min_dist:
                min_dist_sources = []
            if dist < min_dist and dist < empty_unit_range:
                min_dist = dist
                serving_cluster = developing_cluster
                min_dist_sources = sources
        if serving_cluster is not None:
            for source in min_dist_sources:
                developing_clusters_export_requirements[serving_cluster.cluster_id].add(source)
    return developing_clusters_export_requirements


def get_dist_sources_for_export(source_cluster: Cluster, target_cluster: Cluster, mined_resource):
    min_dist = math.inf
    min_dist_sources = []
    for source_pos in source_cluster.reachable_export_positions:
        for target_pos in target_cluster.perimeter:
            if ce.can_mine_on_position(target_cluster, target_pos, mined_resource):
                distance = target_pos.distance_to(source_pos)
                if distance < min_dist:
                    min_dist_sources = []
                if distance <= min_dist:
                    min_dist = distance
                    min_dist_sources.append(source_pos)
    return min_dist, min_dist_sources


def get_my_units_in_clusters(clusters):
    my_units_in_clusters_count = 0
    for cluster_id, c in clusters.items():
        if c.is_me_present:
            for info in c.cell_infos.values():
                my_units_in_clusters_count += len(info.my_units)
    return my_units_in_clusters_count


def get_free_units(my_units_positions, clusters):
    free_units = set(my_units_positions)
    for cluster_id, c in clusters.items():
        if c.is_me_present:
            for pos, info in c.cell_infos.items():
                if info.my_units:
                    free_units.remove(pos)
    return free_units


def get_free_clusters(all_clusters_dict):
    free_clusters = dict()
    for cluster_id, cluster in all_clusters_dict.items():
        if not cluster.is_me_present:
            free_clusters[cluster_id] = cluster
    return free_clusters


def prioritize_all_clusters_for_development(clusters, mined_resource_for_development):
    free_clusters_dict = get_free_clusters(clusters)
    scores_clusters = []
    cluster: Cluster
    for cluster in free_clusters_dict.values():
        cluster_score = cluster.resource_amounts_total["wood"]
        if mined_resource_for_development != "wood":
            cluster_score += cluster.resource_amounts_total["coal"]
            if mined_resource_for_development == "uranium":
                cluster_score += cluster.resource_amounts_total["uranium"]
        scores_clusters.append((cluster_score, cluster))
    scores_clusters.sort(key=lambda x: x[0], reverse=True)
    return scores_clusters


def set_developing_clusters_export_positions(developing_clusters, width):
    for developing_cluster in developing_clusters:
        accessible_positions, export_positions = ce.get_accessible_and_export_positions(developing_cluster, width)
        developing_cluster.set_reachable_export_positions(export_positions)
        developing_cluster.set_reachable_positions(accessible_positions)


def get_remaining_units_allowance(ids_clusters, my_city_tiles, my_free_units):
    my_units_in_clusters_count = get_my_units_in_clusters(ids_clusters)
    return len(my_city_tiles) - my_units_in_clusters_count - len(my_free_units)


def get_cannot_act_units_ids(my_units_dict):
    c = []
    for pos, my_units in my_units_dict.items():
        for my_unit in my_units:
            if not my_unit.can_act():
                c.append(my_unit.id)
    return c
