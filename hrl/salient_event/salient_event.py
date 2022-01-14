import random
import numpy as np
from collections import deque
from pfrl.wrappers import atari_wrappers
from hrl.agent.dsc.datastructures import TrainingExample


class SalientEvent:
    def __init__(self, target_obs, target_pos, tol):
        assert isinstance(tol, float)
        assert isinstance(target_pos, (tuple, np.ndarray))
        assert isinstance(target_obs, atari_wrappers.LazyFrames)

        self.tolerance = tol
        self.target_obs = target_obs
        self.target_pos = np.array(target_pos)
        self.effect_set = deque([TrainingExample(target_obs, target_pos)], maxlen=20)

    def add_to_effect_set(self, obs, pos):
        self.effect_set.append(TrainingExample(obs, pos))

    def get_target_position(self):
        return self.target_pos

    def get_target_obs(self):
        return self.target_obs

    def sample(self):
        """ Sample a state from the effect set. """ 
        if len(self.effect_set) > 0:
            sampled_point = random.choice(self.effect_set)
            return sampled_point.obs, sampled_point.pos
        return self.target_obs, self.target_pos

    def __call__(self, pos):
        if isinstance(pos, dict):
            pos = pos['player_x'], pos['player_y']
            
        xcond = abs(pos[0] - self.target_pos[0]) <= self.tolerance
        ycond = abs(pos[1] - self.target_pos[1]) <= self.tolerance
        return xcond and ycond

    def __str__(self):
        return f"SE({self.target_pos})"
    
    def __repr__(self):
        return str(self)