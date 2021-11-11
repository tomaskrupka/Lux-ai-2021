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
    adjacent_positions = [Position(a, b) for (a, b) in [(p.x - 1, p.y), (p.x + 1, p.y), (p.x, p.y - 1), (p.x, p.y + 1)]]
    return [p for p in adjacent_positions if p in c.cell_infos]


def can_mine_on_position(cluster: Cluster, position: Position, mined_resource):
    cell_info = cluster.cell_infos[position]
    can_mine_here = cell_info.mining_potential['WOOD'] > 0 or \
                    (cell_info.mining_potential['COAL'] > 0 and not mined_resource == 'WOOD') or \
                    (cell_info.mining_potential['URANIUM'] > 0 and mined_resource == 'URANIUM')
    return can_mine_here


def detect_push_out_units_positions(cluster, cluster_development_settings):
    push_out_units = []  # units on push out positions
    push_out_positions = []  # positions to push from to export positions
    for cell_pos, cell_info in cluster.cell_infos.items():
        adjacent_positions_any = extensions.get_adjacent_positions(cell_pos, cluster_development_settings.width)
        adjacent_positions_cluster = get_adjacent_positions_within_cluster(cell_pos, cluster)
        is_next_to_city = any(pos for pos in adjacent_positions_cluster if cluster.cell_infos[pos].my_city_tile)
        is_next_to_export_position = any(
            pos for pos in adjacent_positions_any if pos in cluster_development_settings.units_export_positions)
        is_push_out_position = is_next_to_city and is_next_to_export_position
        if is_push_out_position:
            push_out_positions.append(cell_pos)
            if cell_info.my_units and cell_info.my_units[0].get_cargo_space_left() == 100:
                push_out_units.append(cell_pos)
                if cell_info.my_city_tile:
                    print('error. push out unit in a city.')

    return push_out_units, push_out_positions


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
