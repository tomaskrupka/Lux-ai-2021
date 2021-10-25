def get_free_units(game_state, clusters):
    for cluster in clusters:
        pass


def get_player_city_tiles_xys(player):
    player_city_tiles_xys = []
    for k, city in player.cities.items():
        for tile in city.citytiles:
            player_city_tiles_xys.append((tile.pos.x, tile.pos.y))
    return player_city_tiles_xys
