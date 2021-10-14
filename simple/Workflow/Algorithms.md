#The simple bot
This is a rulebook according to which the 'simple bot' has been programmed.

## Agent
The Agent is a singleton that lives through the whole game.
Agent is the object that takes actions based on the `(observation, configuration)` parameters of every round.


These actions are produced by the following workflow:

1. Identify missions.
1. Identify workers for the missions.
1. `get-actions(mission)` for these workers.
1. `get-actions()` for all other workers.
1. call churn manager
1. append all actions

## Worker
The Worker is the static code (no objects are being instantiated for workers) that drives the behaviour of all the workers as the game objects. Therefore, all workers are clones as they follow the same built-in decision flow for prioritizing possible actions. Following are the principles that govern workers' behaviour.

### Behaviour

workers:

-  are transient and have no memory. A worker only lives as long as its code runs.
1. are *autonomous*, i.e. capable of making a decision in a single run of the Worker code that depends only on the `game_state`,
1. do not account for other workers, both own and opponent's, in their decision making,
1. can evaluate all of their possible actions and order them by their preference and
1. can evaluate their situation at any time.


### Evaluating actions
Worker's interface has a `get_actions(...)` call for evaluating all possible actions under current `game_state`, optionally subject to a mission assignment. Worker returns *all possible actions* ordered by its preference.

#### Parameters
- `game_state`
- `mission` (optional)

#### Evaluation
Worker evaluates its actions in the following order:

1. If a mission has been assigned in the call, this overrides the worker's autonomy. Order possible actions solely by the benefit to the mission.
1. Follow the built-in fallback flow to choose a mission.
1. If the mission is a destination:
	- Identify all positions within this destination,
	- Order all 5 directions by the distance to the nearest of the positions.
1. If the mission is building a city tile, put that action into the ordered list.
1. Complement the list with all unlisted possible actions from secondary missions.

#### Return object
List of all possible actions ordered by worker's preference.

## Churn
## Mission
## City
Cities are passive and transient much like the workers. They calculate and predict various high-level flags, They can signal 


the `update()` method
the `get_actions()` method


### Mission