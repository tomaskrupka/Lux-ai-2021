
# Lux bot

This repo is my submission for the [2021 Lux AI challenge](https://www.lux-ai.org/specs-2021),
exactly as I've submitted it.

## About

This is a bot designed to play a game against another bot.
The rules are [here](https://www.lux-ai.org/specs-2021).

The Kaggle intro puts it this way:

>The Lux AI Challenge is a competition where competitors design agents to tackle a multi-variable optimization, resource gathering, and allocation problem in a 1v1 scenario against other competitors.

### <a name="Agent"></a> Agent
By the game specification, the agent is

>A function which given an observation generates an action.

In other words, each turn the game engine runs the 
[`agent(observation, configuration)`](https://github.com/tomaskrupka/Lux-ai-2021/blob/main/bot_orchestrated/agent.py)
function to 
- provide the agent with the current game state and
- gather its [actions](#action).

### <a name="action"></a> Action

Submitting actions to the game engine is how the agent plays the game.
The actions are specified in the rules,
most of the time it's moving a unit, producing a unit or building a city tile. 

## Rationale

The problem domain of the gameplay is huge.
To split the problem into smaller, focused units that are easier to tackle, 
the bot always follows a set of ground rules
when reading the situation and developing [strategies](#strategy).

1. Each turn the map is split into [clusters](#cluster) and the [open space](#open_space) that fills the rest of the map.
2. [Clusters](#cluster) have full autonomy over their territory and act as an agent on that domain. 
3. [Agent](#agent) has the final authority over the actions submitted to the game engine.

## <a name="cluster"></a> Cluster

Clusters are objects defined around sets of neighboring resource tiles,
city tiles and their perimeter.

1. They have exclusive control over their perimeter, resources and units within.
No one else can submit an action on a unit or a tile within a cluster's territory.
2. Clusters must raise a [flag](#flags) should they need outer intervention.
3. It's the [agent's](#agent) exclusive responsibility to observe the flags and react upon them.

#### <a name="flags"></a>Flags

Clusters have the ability to signal about their state.
The [agent](#agent) will issue [operations](#operation) based on these signals.

- `need_refuel` There's a city in the cluster that can't sustain itself through the upcoming night.
- `can_export` Cluster can export resources.
- `export_positions` Neighboring positions that the cluster is able to export to.

### <a name="open_space"></a> Open space

Open space is the object that is responsible for the tiles that are not part of any cluster.

## <a name="strategy"></a> Strategy

Strategy is a set of rules that govern the bot behavior. These can be tweaked, parametrized and changed.
This way, multiple bots following different strategies
(e.g. aggressive, local, conquering...) can be developed quickly using the same codebase. 

The cookbook for the current implementation is roughly as follows:

- Develop [cities](#city) around [clusters](#cluster).
- Prioritize wood from start of game.
- Try to gain control over whole cluster.
- Build sustainably (avoid dying of cities).

Agent is a rule-based program, no ML involved. Its workflow is as follows:

1. Read situation:
    - Established [clusters](#cluster)
    - Established clusters [flags](#flags)
    - Vacant clusters
    - Free units
2. Based on the situation, develop [operations](#operation).
3. [Order the execution](#execution_order) of the operations.
4. Execute the [open operations](#open_operations), gather resulting actions.
5. Based on the observed shortage of free units when developing and ordering the open operations, assign [units production](#producing_units) to the clusters.
6. Trigger the [Develop operation](#operation-develop) for each cluster, gather resulting actions.
7. Submit all actions.

## <a name="operation"></a>Operations
Operation is a function with encoded objective.
Given the subject and resources it generates actions.
[Agent](#agent) is responsible for identifying the subjects, allocating the resources and triggering the operation.

### <a name="operation_develop"></a>Develop
Clusters use this operation to govern themselves.
[Agent](#agent) triggers this operation for each cluster once every round.

#### Params
- New units request.
- State of perimeter (where it is possible to push new units out).
- Units to pull in (e.g. for refuel).

### Open operations <a name="open_operations"></a>
Operations that are not bound to a specific [cluster](#cluster). Involve missions for one or more free workers.
#### Establish
#### <a name="refuel"></a>Refuel
### <a name="execution_order"></a> Execution order

O

### Multiple workers for one job

Operations are bound to specific actions taking place. That includes specific workers.
Therefore, each operation takes game_state as input and produces game_state as output.

When assigning actions to workers and cities (thus removing these from the pool of available resources),
operations follow hardcoded rules.

## <a name="producing_units"></a>Producing units
[Agent](#agent) can order the production of more units as a parameter to the [Develop operation](#operation_develop).
[Cluster](#cluster) produces  

### Mining
- Prioritize mining next to opponent's city
- Cut opponent from mining positions

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


Not everyone can do everything this way,
but that is a small inconvenience far outweighed by the benefits it has for the development.
- Smaller scope means fewer edge cases to handle.
- Fewer unhandled edge cases mean fewer conflicts to handle.
- resulting from unhandled edge cases
and handle the resulting conflicts afterwards.