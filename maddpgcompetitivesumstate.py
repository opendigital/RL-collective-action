# -*- coding: utf-8 -*-
"""MADDPGCooperativeGameState.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1mnQ2zmvj5FQAcPBaxVGwy3CPfaLM-BrQ
"""

# !pip install gym
# !pip install numpy
# !pip install ray
# !pip install ray[rllib]
# !pip install tabulate

import numpy as np
import gym
import ray
from ray.rllib.models import ModelCatalog
from ray.rllib.models.tf.tf_modelv2 import TFModelV2
from gym.spaces import Discrete, Box, MultiDiscrete
from ray.rllib import MultiAgentEnv

NUM_TRAINING_STEPS = 50000

class CollectiveActionEnv(MultiAgentEnv):
    def __init__(self, return_agent_actions = False, part=False):
        # constants
        self.NUM_TURNS = 5
        self.NUM_AGENTS = 17
        self.MAX_CONTRIBUTION = 10

        # in game stuff
        self.current_turn = 0
        self.total_pot = 0
        self.rewards = [0 for i in range(self.NUM_AGENTS)]
        self.board = np.ndarray(shape=(self.NUM_AGENTS, self.NUM_TURNS))
        for i in range(self.NUM_AGENTS):
            for j in range(self.NUM_TURNS):
                self.board[i][j] = -1

        # environment
        self.observation_space = gym.spaces.Box(low=-self.NUM_AGENTS - 1, high=self.MAX_CONTRIBUTION * self.NUM_AGENTS * self.NUM_TURNS + 1, shape=(1,))
        self.action_space = gym.spaces.Discrete(self.MAX_CONTRIBUTION + 1)
        self.agent_ids = list(range(self.NUM_AGENTS))

    def reset(self):
        self.current_turn = 0
        self.total_pot = 0
        self.rewards = [0 for i in range(self.NUM_AGENTS)]

        for i in range(self.NUM_AGENTS):
            for j in range(self.NUM_TURNS):
                self.board[i][j] = -1

        return self.find_observations()

    def find_observations(self):
        contribution_sum = 0
        for i in range(self.NUM_AGENTS):
            contribution_sum += self.board[i][self.current_turn]
        values = [np.array([contribution_sum]) for i in range(self.NUM_AGENTS)]
        
        return self._make_dict(values)

    def play_game(self, action_dict):
        for i in range(self.NUM_AGENTS):
            all_contributions = [j for j in range(self.MAX_CONTRIBUTION + 1)]
            chosen_action = np.random.choice(a=all_contributions, size=None, replace=True, p=action_dict[i])

            self.board[i][self.current_turn] = float(chosen_action)
            self.total_pot += chosen_action
        
    def find_rewards(self, action_dict):
        # compute everyone's individual rewards
        for i in range(self.NUM_AGENTS):
            chosen_action = self.board[i][self.current_turn]

            amount_saved = self.MAX_CONTRIBUTION - chosen_action
            self.rewards[i] += float(amount_saved)
                
        if self.current_turn == self.NUM_TURNS - 1:
            for i in range(self.NUM_AGENTS):
                self.rewards[i] += 1.6 * self.total_pot / float(self.NUM_AGENTS)
        
        # since our agent is trying to maximize the group good its reward will be the group good
        # total_reward = sum(self.rewards)
        # total_reward_array = [total_reward] * self.NUM_AGENTS

        return self._make_dict(self.rewards)
    
    def find_dones(self):
        done = self.current_turn == self.NUM_TURNS
        values = [done for i in range(self.NUM_AGENTS)]
        dones = self._make_dict(values)
        dones["__all__"] = done

        return dones

    def step(self, action_dict):
        self.play_game(action_dict)
        obs, rew, info = self.find_observations(), self.find_rewards(action_dict), {}
        self.current_turn += 1
        done = self.find_dones()

        return obs, rew, done, info

    def _make_dict(self, values):
        return dict(zip(self.agent_ids, values))

e = CollectiveActionEnv()

actions = {}
DESIRED_CONTRIBUTION = 2
for i in range(e.NUM_AGENTS):
    actions[i] = [0.0 for i in range(e.MAX_CONTRIBUTION + 1)]
    actions[i][DESIRED_CONTRIBUTION] = 1.0 # set the probability that the action 5 is chosen to 1.0

for i in range(5):
    obs, rewards, dones, _ = e.step(actions)
    print(obs[0])
    print(rewards)

from ray.tune.registry import register_env

def env_creator(_):
    return CollectiveActionEnv()

single_env = CollectiveActionEnv()
env_name = "CollectiveActionEnv"
register_env(env_name, env_creator)

obs_space = single_env.observation_space
act_space = single_env.action_space
NUM_AGENTS = single_env.NUM_AGENTS

def gen_policy(i):
    return (None, obs_space, act_space, {'agent_id': i})

policy_graphs = {}

for i in range(NUM_AGENTS):
    policy_graphs['agent-' + str(i)] = gen_policy(i)

def policy_mapping_fn(agent_id):
        return 'agent-' + str(agent_id)

config = {
    "learning_starts": 4000,
    "multiagent": {
        "policies": policy_graphs,
        "policy_mapping_fn": policy_mapping_fn
    },
    "env": "CollectiveActionEnv"
}

from ray.rllib.contrib.maddpg import MADDPGTrainer
from ray.tune.logger import pretty_print
import json

ray.init(num_cpus=None)

trainer = MADDPGTrainer(config=dict(config, **{
        "env": CollectiveActionEnv,
    }), env=CollectiveActionEnv)

policy_means = open('maddpgcompetitivesumstate_policymeans.txt', 'a')
full_results = open('maddpgcompetitivesumstate_results.txt', 'a')
checkpoint_paths = open('maddpgcompetitivesumstate_checkpoints.txt', 'a')

print("Starting training")
for i in range(NUM_TRAINING_STEPS):
    if i % 100 == 0:
        checkpoint = trainer.save()
        print(checkpoint)
        checkpoint_paths.write(str(i) + ": ")
        checkpoint_paths.write(checkpoint)
        checkpoint_paths.write('\n')

    result = trainer.train()

    policy_mean_str = json.dumps(result.get('policy_reward_mean'))
    print(str(i) + ": " + policy_mean_str)
    policy_means.write(policy_mean_str)
    policy_means.write('\n')
    full_results.write(pretty_print(result))
    full_results.write('\n')

policy_means.close()
full_results.close()
checkpoint_paths.close()

print("Completed training")
checkpoint_path = trainer.save()
print(checkpoint_path)

loaded_trainer = MADDPGTrainer(config=dict(config, **{
        "env": CollectiveActionEnv,
    }), env=CollectiveActionEnv)

loaded_trainer.restore(checkpoint_path)

ray.shutdown()