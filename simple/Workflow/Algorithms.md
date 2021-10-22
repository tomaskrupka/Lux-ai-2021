
# Lux bot

Lux bot is a submission for the [2021 Lux AI challenge](https://www.lux-ai.org/specs-2021).

## Rationale
The bot builds on some universal ground rules which provide bounding limitations for developing [strategies](#strategy).
It is only allowed to  

- [Agent](#agent) has the final authority over actions submitted.
- [Clusters](#cluster) have full autonomy over everything within their perimeter.
- Units and cities have 

## <a name="strategy"></a> Strategy

Strategy is a set of rules that

- Develop [cities](#city) around [clusters](#cluster).
- Prioritize wood from start of game.
- Try to gain control over whole cluster.
- Build sustainably (avoid dying of cities).

## <a name="Agent"></a> Agent
By the game specification, the agent is

>A function which given an observation generates an action.

Agent is a rule-based program, no ML involved. 

Its workflow is as follows:

1. Read situation:
    - Established [clusters](#cluster)
    - Established clusters [flags](#flags)
    - Vacant clusters
    - Free units
2. Based on the situation, develop [operations](#operation).
3. Figure out how to [order the execution](#execution_order) of the operations.
4. Based on the observed shortage of free units assign [units production](#producing_units) to the clusters.
5. Trigger the [Develop operation](#operation-develop) for each cluster.
6. Submit all actions.

## <a name="cluster"></a> Cluster

Clusters govern themselves.

1. They have exclusive (no one else can) control over their perimeter, resources, units within.
2. It's their exclusive responsibility to raise a [flag](#flags) should they need outer intervention.
3. It's the [agent's](#agent) exclusive responsibility to observe the flags and react upon them.

### <a name="flags"></a>Flags

Clusters have the ability to signal about their state.
The [agent](#agent) will issue [operations](#operation) based on these signals.

- `Refuel(city)` City can't sustain itself through the upcoming night.

## <a name="city"></a>City
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

### Unconditional operations
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