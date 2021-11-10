from cluster import Cluster


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
