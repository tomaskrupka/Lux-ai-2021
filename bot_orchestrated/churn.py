import math
import extensions


def solve_churn_with_score(positions_options: [], positions_scores: []):
    move_solutions = dict()
    high_score = -math.inf
    valid_positions_options = []
    for position, options in positions_options:
        if len(options) > 0:
            valid_positions_options.append([position, options])
    if len(valid_positions_options) == 0:
        return move_solutions, 0
    for position, options in valid_positions_options:
        for option in options:
            positions_options_reduction = get_position_options_reduction(valid_positions_options, position,
                                                                         option).items()
            if len(positions_options_reduction) > 0:
                move_solutions_reduction, score = solve_churn_with_score(positions_options_reduction, positions_scores)
                pos_opt_score = score + positions_scores[option]
                if pos_opt_score > high_score:
                    high_score = pos_opt_score
                    move_solutions = move_solutions_reduction
                    if position in move_solutions:
                        move_solutions[position].append(option)
                    else:
                        move_solutions[position] = [option]
            else:
                pos_opt_score = positions_scores[option]
                if pos_opt_score > high_score:
                    high_score = pos_opt_score
                    move_solutions[position] = [option]

    return move_solutions, high_score


def get_position_options_reduction(positions_options, pos_to_remove, opt_to_remove):
    positions_options_reduction = dict()
    for position, options in positions_options:
        if position != pos_to_remove:
            for option in options:
                if option != opt_to_remove:
                    if position in positions_options_reduction:
                        positions_options_reduction[position].append(option)
                    else:
                        positions_options_reduction[position] = [option]
    return positions_options_reduction


def get_move_actions_with_blocks(positions_options, moves_solutions, cluster):
    positions_units = dict()
    for position, options in positions_options:
        if position in positions_units:
            used_units = len(positions_units[position])
            positions_units[position].append(cluster.cell_infos[position].my_units[used_units])
        else:
            positions_units[position] = [cluster.cell_infos[position].my_units[0]]
    blocked_positions = []
    actions = []
    for position in positions_units:
        if position in moves_solutions:
            for move, unit in zip(moves_solutions[position], positions_units[position]):
                direction = extensions.get_directions_to_target(position, move)
                actions.append(unit.move(direction))
                blocked_positions.append((position, move))
            if len(moves_solutions[position]) < len(positions_units[position]):
                blocked_positions.append((position, position))
        else:
            blocked_positions.append((position, position))
    return actions, blocked_positions
