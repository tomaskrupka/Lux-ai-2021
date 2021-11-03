if __package__ == "":
    # for kaggle-environments
    from lux.game import Game
    from lux.constants import Constants
    from lux import annotate
    import cluster
    import recon

else:
    # for CLI tool
    from .lux.game import Game
    from .lux.game_map import Cell
    from .lux.constants import Constants
    from .lux import annotate
    from . import cluster
    from . import recon

DIRECTIONS = Constants.DIRECTIONS
game_state = None

def agent(observation, configuration):
    global game_state

    ### Do not edit ###
    if observation["step"] == 0:
        game_state = Game()
        game_state._initialize(observation["updates"])
        game_state._update(observation["updates"][2:])
        game_state.id = observation.player
    else:
        game_state._update(observation["updates"])

    actions = []

    ### AI Code goes down here! ###

    # Read situation

    me = game_state.players[observation.player]
    opponent = game_state.players[(observation.player + 1) % 2]
    my_city_tiles = recon.get_player_city_tiles(me)
    opponent_city_tiles = recon.get_player_city_tiles(opponent)
    my_units = recon.get_player_unit_tiles(me)
    opponent_units = recon.get_player_unit_tiles(opponent)
    clusters = recon.detect_clusters(game_state, me, my_city_tiles, opponent_city_tiles, my_units, opponent_units)
    my_units_count = 0
    for c in clusters:
        for pos, info in c.cell_infos.items():
            my_units_count += len(info.my_units)
    remaining_units_allowance = len(my_city_tiles) - my_units_count
    for c in clusters:
        actions = actions + cluster.develop_cluster(c, cluster.ClusterDevelopmentSettings(
            units_build_allowance=remaining_units_allowance))[0]


    # you can add debug annotations using the functions in the annotate object
    # actions.append(annotate.circle(0, 0))

    return actions