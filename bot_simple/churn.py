import extensions


class UnitActions:
    def __init__(self, unit, positions):
        self.unit = unit
        self.positions = positions


# 1 if one of moves towards target possible, do it

# 2 TODO if not, try to switch targets with colliding unit

# 3 if not possible, pick another action from list

def solve_churn(units_actions):
    actions = {}
    for unit_actions in units_actions:
        unit_solved = False
        position = unit_actions.unit.pos
        for new_pos in unit_actions.positions:
            directions = extensions.get_directions_to_target(unit_actions.unit.pos, new_pos)
            # collisions = {}
            for direction in directions:
                new_pos = extensions.get_new_position(position, direction)
                new_pos_tuple = (new_pos.x, new_pos.y)
                colliding_unit_data = actions[new_pos_tuple]
                if colliding_unit_data is None:
                    actions[new_pos_tuple] = (unit_actions.unit, position)
                    unit_solved = True
                    break
                # else:
                #     collisions[new_pos_tuple] = colliding_unit_data
            if unit_solved:
                break
        if not unit_solved:
            pass
    return actions




