import math

if __package__ == "":
    # for kaggle-environments
    from lux.game import Game
    from lux.constants import Constants
    from lux import annotate
    import cluster
    import recon
    import extensions

else:
    # for CLI tool
    from .lux.game import Game
    from .lux.game_map import Cell
    from .lux.constants import Constants
    from .lux import annotate
    from . import cluster, extensions
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

    # Recon
    me = game_state.players[observation.player]
    opponent = game_state.players[(observation.player + 1) % 2]
    my_city_tiles = recon.get_player_city_tiles(me)
    opponent_city_tiles = recon.get_player_city_tiles(opponent)
    my_units = recon.get_player_unit_tiles(me)
    opponent_units = recon.get_player_unit_tiles(opponent)
    clusters = recon.detect_clusters(game_state, me, my_city_tiles, opponent_city_tiles, my_units, opponent_units)
    my_units_count = 0

    # Recon free units
    free_units = set(my_units.keys())
    free_clusters = []
    for cluster_id, c in clusters.items():
        for pos, info in c.cell_infos.items():
            units_count = len(info.my_units)
            my_units_count += units_count
            if units_count > 0:
                free_units.remove(pos)
    remaining_units_allowance = len(my_city_tiles) - my_units_count
    for cluster_id, c in clusters.items():
        if not c.is_me_present:
            free_clusters.append(c)

    # Send free units to empty cities
    for free_unit in free_units:
        if my_units[free_unit][0].can_act():
            if free_clusters:
                min_distance_cluster, min_distance_pos = recon.get_closest_cluster(free_unit, free_clusters)
                direction = extensions.get_directions_to_target(free_unit, min_distance_pos)
                actions.append(my_units[free_unit][0].move(direction))
                free_clusters.remove(min_distance_cluster)
            else:
                print('todo: free unit has nowhere to go')
                # TODO: free unit has nowhere to go.
    needed_units = len(free_clusters)
    # export units for empty cities not served by free units
    developing_clusters = [c for c in clusters.values() if c.is_me_present]
    for developing_cluster in developing_clusters:
        export_positions = []
        export_units_count = 0
        if free_clusters:
            best_free_cluster_score = math.inf
            taken_free_cluster = None
            best_export_positions = []
            for free_cluster in free_clusters:
                export_positions = recon.get_cluster_export_positions_for_free_cluster(
                    free_cluster=free_cluster,
                    exporting_cluster=developing_cluster,
                    w=game_state.map_width)
                if export_positions:
                    cluster_score = export_positions[0][1]
                    if cluster_score < best_free_cluster_score:
                        best_free_cluster_score = cluster_score
                        taken_free_cluster = free_cluster
                        best_export_positions = export_positions
            free_clusters.remove(taken_free_cluster)
            export_positions = [ep[0] for ep in best_export_positions]
            export_units_count = 1
        actions = actions + cluster.develop_cluster(developing_cluster, cluster.ClusterDevelopmentSettings(
            units_build_allowance=remaining_units_allowance,
            units_export_positions=export_positions,
            units_export_count=export_units_count,
            upcoming_cycles=[],
            research_level=0,
            width=game_state.map_width))[0]

    # you can add debug annotations using the functions in the annotate object
    # actions.append(annotate.circle(0, 0))

    return actions
