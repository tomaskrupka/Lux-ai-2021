
# Lux bot

Lux bot is a submission for the [2021 Lux AI challenge](https://www.lux-ai.org/specs-2021).

## Agent
By the game specification, the agent is

>A function which given an observation generates an action.

Agent is a rule-based program, no ML involved. 

Its workflow is as follows:

1. Read situation:
   - Identify resource clusters.
   - Identify worker clusters.
   - Classify my cities.
   - Classify opponent's cities.
2. Based on the situation, develop operations.
3. Score operations by importance.
4. Create permutations of the list, calculating the **importance cost** of each permutation
(how much are we prioritizing unimportant strategies by executing them in this order).
5. Calculate **feasibility score** for each permutation of the strategies (order of execution) by
   - assigning specific workers to the strategy
   - removing them from the pool of available units (next strategy in this permutation shall not be able to 
   use these workers). <!-- This is wasteful if strategy does not care which worker to use. -->
   - blocking worker's new position (next strategy won't be able to use this position)
   - doing a few runs of this with different workers and moves from same churn cluster
   to mitigate the risk of rejecting (scoring low) a viable permutation just due to churn.
6. Identify missions
7. Identify the best order of execution using each one's importance cost and feasibility score.
8. Assign one mission to one worker based on his ability to do that and how much effort will that be.


## Rationale
These are the main rules the bot tries to observe.
Most of the time some scoring is necessary to find a way out of contradictory objectives.

- Build cities next to clusters.
- Prioritize wood from start of game.
- Try to gain control over whole cluster.
- Build sustainably (avoid dying of cities).

## Operations
Operations are bound to specific actions taking place. That includes specific workers.
Therefore, each operation takes game_state as input and produces game_state as output.

When assigning actions to workers and cities (thus removing these from the pool of available resources),
operations follow hardcoded rules.

- develop existing city (e.g. to secure a cluster)
- start new city
- refuel city
- block opponent from proceeding

## Operations
### Expand existing city
Build more city tiles adjacent to those existing in this city.
Every city that `can_develop()` raises this operation.
#### Missions
- Mine
### Start new city
### Refuel city
## Resources
The fact that a unit is in a city (or close) is a resource, it means that it will be easier to refuel.
Penalty for abandoning city?
City shall signal whether it's able to spawn new units at reasonable pace


- mine for a city
- mine for yourself
- build a city tile

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
ker based on his ability to do that and how much effort will that be.