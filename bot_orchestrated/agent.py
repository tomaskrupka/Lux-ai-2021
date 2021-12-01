import math
import sys

if __package__ == "":
    # for kaggle-environments
    from lux.game import Game
    from lux.constants import Constants
    from lux import annotate
    import cluster
    import recon
    import extensions
    import develop_cluster
    import cluster_extensions
    import agent_extensions
    import agent_actions

else:
    # for CLI tool
    from .lux.game import Game
    from .lux.game_map import Cell
    from .lux.constants import Constants
    from .lux import annotate
    from . import cluster, extensions, develop_cluster, cluster_extensions, agent_extensions, agent_actions
    from . import recon

DIRECTIONS = Constants.DIRECTIONS
game_state = None


def agent(observation, configuration):
    global game_state

    try:

        ### Do not edit ###
        if observation["step"] == 0:
            game_state = Game()
            game_state._initialize(observation["updates"])
            game_state._update(observation["updates"][2:])
            game_state.id = observation.player
        else:
            game_state._update(observation["updates"])
            game_state.turn = observation["step"]

        actions = []

        ### AI Code goes down here! ###

        # Recon
        me = game_state.players[observation.player]
        opponent = game_state.players[(observation.player + 1) % 2]
        my_city_tiles_dict, my_city_tiles_count = recon.get_player_city_tiles(me)
        opponent_city_tiles_dict, opponent_city_tiles_count = recon.get_player_city_tiles(opponent)
        my_units = recon.get_player_unit_positions(me)  # pos = [unit]
        opponent_units = recon.get_player_unit_positions(opponent)
        clusters = recon.detect_clusters(game_state, my_city_tiles_dict, opponent_city_tiles_dict, my_units,
                                         opponent_units)  # id = cluster
        my_free_units = agent_extensions.get_free_units(my_units, clusters)
        remaining_units_allowance = agent_extensions.get_remaining_units_allowance(clusters, my_city_tiles_dict,
                                                                                   my_free_units)
        unmoved_free_units = my_free_units
        blocked_positions = []
        cannot_act_units_ids = agent_extensions.get_cannot_act_units_ids(my_units)

        # CALCULATE CLUSTERS EXPORT POSITIONS

        developing_clusters = [c for c in clusters.values() if c.is_me_present]
        agent_extensions.set_developing_clusters_export_positions(developing_clusters, game_state.map_width)

        # IDENTIFY AND PRIORITIZE FREE CLUSTERS

        scores_free_clusters = agent_extensions.prioritize_all_clusters_for_development(
            clusters,
            extensions.get_mined_resource_for_cluster_development(me.research_points, game_state.turn, my_city_tiles_count))  # [(score, cluster)]
        free_clusters = [c for s, c in scores_free_clusters]

        # SEND FREE UNITS TO CLUSTERS

        if game_state.turn == 44:
            print('my turn')

        if free_clusters:
            blocked_positions = []
            a, b, c, unmoved_units, clusters_ids_units = agent_actions.send_free_units_to_empty_clusters(
                my_free_units,
                scores_free_clusters,
                my_units,
                game_state.turn,
                blocked_positions,
                cannot_act_units_ids)

            actions += a
            blocked_positions += b
            cannot_act_units_ids += c



        # SEND UNMOVED UNITS TO CLOSEST CLUSTER

        a, b, c, unmoved_units = agent_actions.send_units_to_closest_cluster(
            unmoved_free_units,
            clusters.values(),
            my_units,
            blocked_positions,
            cannot_act_units_ids,
            game_state.turn)

        actions += a
        blocked_positions += b
        cannot_act_units_ids += c

        # CALCULATE EXPORT REQUESTS FOR DEVELOPING CLUSTERS

        # todo: calculate with clusters_ids_units (free units that are already on their way)

        mined_resource = extensions.get_mined_resource(me.research_points)
        clusters_export_requirements = agent_extensions.assign_clusters_for_export(
            developing_clusters,
            free_clusters,
            mined_resource,
            game_state.turn)

        # DEVELOP CLUSTERS

        a, remaining_units_allowance = agent_actions.develop_clusters(
            developing_clusters,
            clusters_export_requirements,
            remaining_units_allowance,
            me.research_points,
            game_state)

        actions += a

        # you can add debug annotations using the functions in the annotate object
        # actions.append(annotate.circle(0, 0))

        return actions

    except:
        print("Unexpected error:", sys.exc_info()[0])
        raise
