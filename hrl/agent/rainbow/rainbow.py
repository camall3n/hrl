import torch
import numpy as np
from pfrl import nn as pnn
from pfrl import replay_buffers
from pfrl import agents, explorers
from pfrl.q_functions import DistributionalDuelingDQN


class Rainbow:
    def __init__(self, n_actions, n_atoms, v_min, v_max, noisy_net_sigma, lr, 
                 n_steps, betasteps, replay_start_size, gpu):
        self.n_actions = n_actions

        self.q_func = DistributionalDuelingDQN(n_actions, n_atoms, v_min, v_max)
        pnn.to_factorized_noisy(self.q_func, sigma_scale=noisy_net_sigma)

        explorer = explorers.Greedy()
        opt = torch.optim.Adam(self.q_func.parameters(), lr, eps=1.5e-4)

        self.rbuf = replay_buffers.PrioritizedReplayBuffer(
            10 ** 6,
            alpha=0.5, 
            beta0=0.4,
            betasteps=betasteps,
            num_steps=n_steps,
            normalize_by_max="memory"
        )

        self.agent = agents.CategoricalDoubleDQN(
            self.q_func,
            opt,
            self.rbuf,
            gpu=gpu,
            gamma=0.99,
            explorer=explorer,
            minibatch_size=32,
            replay_start_size=replay_start_size,
            target_update_interval=32_000,
            update_interval=4,
            batch_accumulator="mean",
            phi=self.phi
        )

        self.T = 0

    @staticmethod
    def phi(x):
        """ Observation pre-processing for convolutional layers. """
        return np.asarray(x, dtype=np.float32) / 255.

    def act(self, state):
        """ Action selection method at the current state. """
        return self.agent.act(state)

    def step(self, state, action, reward, next_state, done, reset=False):
        """ Learning update based on a given transition from the environment. """
        self._overwrite_pfrl_state(state, action)
        self.agent.observe(next_state, reward, done, reset)

    def _overwrite_pfrl_state(self, state, action):
        """ Hack the pfrl state so that we can call act() consecutively during an episode before calling step(). """
        self.agent.batch_last_obs = [state]
        self.agent.batch_last_action = [action]

    def experience_replay(self, trajectory):
        """ Add trajectory to the replay buffer and perform agent learning updates. """

        for transition in trajectory:
            self.step(*transition)

    def rollout(self, env, state, episode, max_reward_so_far):
        """ Single episodic rollout of the agent's policy. """

        done = False
        reset = False
        episode_length = 0
        episode_reward = 0.
        episode_trajectory = []

        while not done and not reset:
            action = self.act(state)
            next_state, reward, done, info  = env.step(action)
            reset = info.get("needs_reset", False)

            episode_trajectory.append((state,
                                       action,
                                       np.sign(reward), 
                                       next_state, 
                                       done, 
                                       reset))

            self.T += 1
            episode_length += 1
            episode_reward += reward

            state = next_state

        self.experience_replay(episode_trajectory)
        max_reward_so_far = max(episode_reward, max_reward_so_far)
        print(f"Episode: {episode}, T: {self.T}, Reward: {episode_reward}, Max reward: {max_reward_so_far}")        

        return episode_reward, episode_length, max_reward_so_far