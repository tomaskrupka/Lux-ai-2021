import extensions
from cluster import Cluster
from lux.game_map import Position


def get_units_needed_for_maintenance(c: Cluster):
    serviceable_positions = 0
    has_units_count = 0
    for pos, cell_info in c.cell_infos.items():
        if cell_info.my_units:
            has_units_count += len(cell_info.my_units)
        if cell_info.my_city_tile or cell_info.resource:
            serviceable_positions += 1
    optimal_units_count = serviceable_positions / 6
    return optimal_units_count, has_units_count


def get_mined_resource(research_level):
    mined_resource = 'WOOD'
    if research_level >= 50:
        mined_resource = 'COAL'
    if research_level >= 200:
        mined_resource = 'URANIUM'
    return mined_resource


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


def detect_push_out_units_positions(cluster, cluster_development_settings):
    push_out_units = set()  # units that can be pushed out
    push_out_positions = set()  # positions without units to push from to export positions

    for export_position in cluster_development_settings.units_export_positions:
        for cell_pos, cell_info in get_adjacent_positions_within_cluster(export_position, cluster):
            # adjacent_positions_any = extensions.get_adjacent_positions(cell_pos, cluster_development_settings.width)
            adjacent_positions_cluster = get_adjacent_positions_within_cluster(cell_pos, cluster)
            is_next_to_city = any(pos for pos in adjacent_positions_cluster if cluster.cell_infos[pos].my_city_tile)
            if is_next_to_city:
                if not cell_info.my_units:
                    push_out_positions.add(cell_pos)
                elif cell_info.my_units[0].get_cargo_space_left() == 100:
                    push_out_units.add(cell_pos)

    return list(push_out_units), list(push_out_positions)


def get_cannot_act_units(cluster):
    cannot_act_units = []
    for cell_pos, cell_info in cluster.cell_infos.items():
        if not cell_info.my_city_tile:
            if cell_info.my_units:
                if not cell_info.my_units[0].can_act():
                    cannot_act_units.append(cell_pos)
    return cannot_act_units


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
