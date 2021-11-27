import extensions
from cluster import Cluster
from lux.game_map import Position


def get_units_needed_for_maintenance(c: Cluster):
    # serviceable_positions = 0
    has_units_count = 0
    for pos, cell_info in c.cell_infos.items():
        if cell_info.my_units:
            has_units_count += len(cell_info.my_units)
        # if cell_info.my_city_tile or cell_info.resource:
        #     serviceable_positions += 1
    optimal_units_count = min(len(c.cell_infos) / 8, len(c.resource_positions))
    return optimal_units_count, has_units_count


def get_adjacent_city_tiles_positions(cluster: Cluster, p: Position):
    return [p for p in get_adjacent_positions_within_cluster(p, cluster) if cluster.cell_infos[p].my_city_tile]


def get_adjacent_development_positions(cluster: Cluster, p: Position):
    adjacent_development_positions = []
    for q in cluster.perimeter:
        if cluster.cell_infos[q].is_empty and p.is_adjacent(q):
            adjacent_development_positions.append(q)
    return adjacent_development_positions


def get_adjacent_mining_positions(cluster: Cluster, p: Position, mined_resource):
    adjacent_mining_positions = []
    for cell_pos in cluster.cell_infos:
        if p.is_adjacent(cell_pos) and (can_mine_on_position(cluster, cell_pos, mined_resource)):
            adjacent_mining_positions.append(cell_pos)
    return adjacent_mining_positions


def get_adjacent_positions_within_cluster(p: Position, c: Cluster):
    adjacent_positions_within_cluster = []
    for cluster_pos in c.cell_infos:
        if cluster_pos.x == p.x or cluster_pos.y == p.y:
            if cluster_pos.x - p.x == 1 or p.x - cluster_pos.x == 1 or cluster_pos.y - p.y == 1 or p.y - cluster_pos.y == 1:
                adjacent_positions_within_cluster.append(cluster_pos)
    return adjacent_positions_within_cluster


def can_mine_on_position(cluster: Cluster, position: Position, mined_resource):
    cell_info = cluster.cell_infos[position]
    can_mine_here = cell_info.mining_potential['WOOD'] > 0 or \
                    (cell_info.mining_potential['COAL'] > 0 and not mined_resource == 'WOOD') or \
                    (cell_info.mining_potential['URANIUM'] > 0 and mined_resource == 'URANIUM')
    return can_mine_here


def detect_push_out_units_positions_anywhere(cluster, cluster_development_settings):
    push_out_units = set()  # units that can be pushed out
    push_out_positions = set()  # positions without units to push from to export positions

    for export_position in cluster_development_settings.units_export_positions:
        for cell_pos in get_adjacent_positions_within_cluster(export_position, cluster):
            cell_info = cluster.cell_infos[cell_pos]
            if not cell_info.my_units:
                push_out_positions.add(cell_pos)
            else:
                push_out_units.add(cell_pos)

    return push_out_units, push_out_positions


def detect_push_out_units_positions_next_to_cities(cluster, cluster_development_settings):
    push_out_units = set()  # units that can be pushed out
    push_out_positions = set()  # positions without units to push from to export positions

    for export_position in cluster_development_settings.units_export_positions:
        for cell_pos in get_adjacent_positions_within_cluster(export_position, cluster):
            # adjacent_positions_any = extensions.get_adjacent_positions(cell_pos, cluster_development_settings.width)
            adjacent_positions_cluster = get_adjacent_positions_within_cluster(cell_pos, cluster)
            is_next_to_city = any(pos for pos in adjacent_positions_cluster if cluster.cell_infos[pos].my_city_tile)
            if is_next_to_city:
                cell_info = cluster.cell_infos[cell_pos]
                if not cell_info.my_units:
                    push_out_positions.add(cell_pos)
                elif cell_info.my_units[0].get_cargo_space_left() == 100:
                    push_out_units.add(cell_pos)

    return list(push_out_units), list(push_out_positions)


def get_cannot_act_units(cluster):
    b = []
    c = []
    for cell_pos, cell_info in cluster.cell_infos.items():
        for unit in cell_info.my_units:
            if not unit.can_act():
                b.append(cell_pos)
                c.append(unit.id)
    return b, c


def get_cities_fuel_balance(cluster: Cluster, nights):
    cities_by_fuel = dict()
    for pos, info in cluster.cell_infos.items():
        if info.my_city:
            city = info.my_city
            if city.cityid not in cities_by_fuel:
                cities_by_fuel[city.cityid] = (city.fuel - city.light_upkeep * nights, [pos])
            else:
                cities_by_fuel[city.cityid][1].append(pos)
    return cities_by_fuel


def get_mining_potential_aggregate(mining_potential, mined_resource):
    if mined_resource == 'WOOD':
        return mining_potential['WOOD'] * 20
    elif mined_resource == 'COAL':
        return mining_potential['WOOD'] * 20 + mining_potential['COAL'] * 50
    elif mined_resource == 'URANIUM':
        return mining_potential['WOOD'] * 20 + mining_potential['COAL'] * 50 + mining_potential['URANIUM'] + 80


def get_blocked_positions_now(cluster, blocked_positions, cannot_act_units_ids):
    blocked_positions_now = []
    for p in cluster.cell_infos:
        if p in blocked_positions:
            blocked_positions_now.append(p)
            continue
        cell_info = cluster.cell_infos[p]
        # allow occupied where unit moved out.
        if cell_info.my_units and cell_info.my_units[0].id not in cannot_act_units_ids:
            blocked_positions_now.append(p)
    return blocked_positions_now


def get_reachable_perimeter(cluster: Cluster):
    reachable_perimeter = []
    for p in cluster.perimeter:
        for adj_pos in get_adjacent_positions_within_cluster(p, cluster):
            if cluster.cell_infos[adj_pos].my_units:
                reachable_perimeter.append(p)
    return reachable_perimeter


def get_accessible_and_export_positions(cluster, w):
    accessible_positions = get_accessible_positions(cluster)
    export_positions = set()
    for pos in accessible_positions.intersection(cluster.perimeter):
        for adj_pos in extensions.get_adjacent_positions(pos, w):
            if adj_pos not in cluster.cell_infos:
                export_positions.add(adj_pos)
    return accessible_positions, export_positions


def get_accessible_positions(cluster: Cluster):
    accessible_positions = set()

    def _add_adjacent_accessible_positions(p):
        adjacent_positions = get_adjacent_positions_within_cluster(p, cluster)
        for adj_pos in adjacent_positions:
            if adj_pos not in accessible_positions:
                adj_info = cluster.cell_infos[adj_pos]
                if not adj_info.opponent_city_tile:
                    accessible_positions.add(adj_pos)
                    _add_adjacent_accessible_positions(adj_pos)

    for pos in cluster.cell_infos:
        if cluster.cell_infos[pos].my_units:
            _add_adjacent_accessible_positions(pos)
    return accessible_positions


def get_cities_scores_mineability(cluster: Cluster, mined_resource):
    # identify cities
    cities = dict()  # id = city
    for cell_pos, cell_info in cluster.cell_infos.items():
        if cell_info.my_city:
            cities[cell_info.my_city.cityid] = cell_info.my_city
    # score cities
    cities_scores = dict()  # id = city_score
    cities_mineabilities = dict()
    for city_id, city in cities.items():
        city_score = 0
        city_mineability = dict()
        for city_tile in city.citytiles:
            city_score += 1 - len(cluster.cell_infos[city_tile.pos].my_units)
            city_mineability[city_tile.pos] = get_mining_potential_aggregate(
                cluster.cell_infos[city_tile.pos].mining_potential, mined_resource)
        cities_mineabilities[city_id] = city_mineability
        cities_scores[city_id] = city_score
    return cities, cities_scores, cities_mineabilities


def get_opponent_city_tiles(cluster: Cluster):
    b = []
    for pos, info in cluster.cell_infos.items():
        if info.opponent_city_tile:
            b.append(pos)
    return b

