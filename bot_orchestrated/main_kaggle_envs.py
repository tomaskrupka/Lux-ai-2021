from kaggle_environments import make
from agent import agent

env = make("lux_ai_2021", configuration={"seed": 0, "loglevel": 2, "annotations": True}, debug=True)
steps = env.run([agent, agent])
