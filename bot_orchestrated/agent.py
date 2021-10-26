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

    player = game_state.players[observation.player]
    opponent = game_state.players[(observation.player + 1) % 2]
    my_city_tiles_xys = recon.get_player_city_tiles_xys(player)
    opponent_city_tiles_xys = recon.get_player_city_tiles_xys(opponent)
    clusters = recon.detect_clusters(game_state, player, my_city_tiles_xys, opponent_city_tiles_xys)


    # you can add debug annotations using the functions in the annotate object
    # actions.append(annotate.circle(0, 0))

    return actions