import cluster_extensions
from cluster import CellInfo


def build_workers_or_research(cluster, cluster_development_settings):
    units_allowance = cluster_development_settings.units_build_allowance
    researched = 0  # Prevent researching past 200 here and in other clusters
    units_needed, has_units = cluster_extensions.get_units_needed_for_maintenance(cluster)
    units_surplus = has_units - units_needed - cluster_development_settings.units_export_count
    units_surplus_balance = units_surplus
    actions = []
    for city_cell in [cell_info for cell_coords, cell_info in cluster.cell_infos.items() if cell_info.my_city_tile]:
        if city_cell.my_city_tile.can_act():
            if units_surplus_balance < 0 < units_allowance:
                actions.append(city_cell.my_city_tile.build_worker())
                units_allowance -= 1
                units_surplus_balance += 1
            elif cluster_development_settings.research_level + researched < 200:
                actions.append(city_cell.my_city_tile.research())
                researched += 1
    return actions, units_allowance, units_surplus, researched


def get_cannot_act_units(cluster):
    cannot_act_units = []
    for cell_pos, cell_info in cluster.cell_infos.items():
        if not cell_info.my_city_tile:
            if cell_info.my_units:
                if not cell_info.my_units[0].can_act():
                    cannot_act_units.append(cell_pos)
    return cannot_act_units


def build_city_tiles(cluster):
    actions = []
    blocked_empty_tiles = []
    for cell_pos, cell_info in cluster.cell_infos.items():
        if cell_info.is_empty and cell_info.my_units:
            unit = cell_info.my_units[0]
            blocked_empty_tiles.append(cell_pos)
            if unit.can_act() and unit.get_cargo_space_left() == 0:
                actions.append(unit.build_city())
    return actions, blocked_empty_tiles
