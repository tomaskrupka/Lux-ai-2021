#Lux bot

Lux bot is a submission for the [2021 Lux AI challenge](https://www.lux-ai.org/specs-2021). 
It's a rule-based program, no ML involved.

## High-level strategy
These are the main rules the bot tries to observe.
Most of the time some scoring is necessary to find a way out of contradictory objectives.

- Build cities next to clusters.
- Prioritize wood from start of game.
- Try to gain control over whole cluster.
- Build sustainably (avoid dying of cities).

## Operations
- develop existing city (e.g. to secure a cluster)
- start new city
- refuel city
- block opponent from proceeding

### Mining
- Prioritize mining next to opponent's city
- Cut opponent from mining positions

### City
- If sharing, mine as much as possible regardless of resource type
- Optimize unit production x research
- If occupying whole cluster
  - Optimize for maximum size at end of game
  - If wood, account for regrowth

#### Interface
- How many workers can you possibly employ
- How long do you need to secure cluster, how long without certain worker(s)
- If cluster secured, how many workers do you need to sustain

#### Building
Proceed so that the city can be locked into a sustainable formation.

#### Classification
- out of reach of resource
- within reach or next to a resource
  - not sharing, not controlling
  - controlling whole cluster
  - sharing cluster
  - unsustainable

### Cluster

## Agent

By the game specification, the agent is

>A function which given an observation generates an action.

Its gameplay in this implementation is as follows:

- Read situation:
  - Identify clusters.
  - Identify churn clusters (of workers).
  - Classify my cities.
  - Classify opponent's cities.
- Based on the situation, develop operations
- For each operation score workers by usefulness for the job.
- Score operations by importance 
- create permutations of the list, calculating the *importance cost* of each permutation 
(how much are we prioritizing unimportant strategies by executing them in this order).
- calculate *feasibility score* for each permutation of the strategies (order of execution) by
  - assigning specific workers to the strategy
  - removing them from the pool of available units (next strategy in this permutation shall not be able to 
  use these workers). <!-- This is wasteful if strategy does not care which worker to use. -->
  - blocking worker's new position (next strategy won't be able to use this position)
  - doing a few runs of this with different workers and moves from same churn cluster
  to mitigate the risk of rejecting (scoring low) a viable permutation just due to churn.
- identify missions
  - mine for a city
  - mine for yourself
  - build a city tile 
- identify the best order of execution using each one's importance cost and feasibility score.
- assign one mission to one worker based on his ability to do that and how much effort will that be.

## Agent
By the game specification, agent has to be

>A function which given an observation generates an action.

Its workflow is as follows:

1. Identify missions.
1. Assign workers to the missions.
1. `get-actions(mission)` for the workers that have been assigned a mission.
1. `get-actions()` for all other workers.
1. call churn manager
1. append all actions

## Worker

The Worker is the static code (no objects are being instantiated for workers) that drives the behaviour of all the workers as the game objects. Therefore, all workers are clones as they follow the same built-in decision flow for prioritizing possible actions. Following are the principles that govern workers' behaviour.

### Behaviour

Workers:

-  are transient and have no memory. A worker only lives as long as its code runs.
1. are *autonomous*, i.e. capable of making a decision in a single run of the Worker code that depends only on the `game_state`,
1. do not account for other workers, both own and opponent's, in their decision-making,
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

- read situation:
  - clusters
  - my cities
  - opponent's cities
  - my units
  - opponent's units
- identify strategies
  - develop existing city (e.g. to occupy cluster)
  - build new city
  - refuel city
  - block opponent from proceeding
- score strategies by importance and create permutations of the list, calculating the *importance cost* of each permutation 
(how much are we prioritizing unimportant strategies by executing them in this order).
- calculate *feasibility score* for each permutation of the strategies (order of execution), assigning specific workers
to the strategy, removing them from the pool of available units (next strategy in this permutation shall not be able to 
use these workers).
  - identify missions
    - mine for a city
    - mine for yourself
    - build a city tile 
- identify the best order of execution using each one's importance cost and feasibility score.
- assign one mission to one worker based on his ability to do that and how much effort will that be.