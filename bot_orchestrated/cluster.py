from typing import NamedTuple


class Cluster:
    coordinates = set()
    units = []
    cities = []

    def __init__(self, coordinates_list):
        for (x, y) in coordinates_list:

            CellInfo(x, y, )

class CellInfo(NamedTuple):
    x: int
    y: int
    is_empty: bool
    is_my_city_tile: bool
    is_opponent_city_tile: bool
    is_resource: bool
    resource_type: str
    resource_value: int