import numpy as np
import pandas as pd
import torch
import os
from collections import deque

from stable_baselines3.common.noise import NormalActionNoise
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv
from stable_baselines3 import SAC
from stable_baselines3.common.callbacks import BaseCallback, CallbackList

# For training, tuning, logging and experimentation purposes
# from sb3_contrib import RecurrentPPO
# from wandb.integration.sb3 import WandbCallback
# from ray import tune, train


# TODO : Need to Integrate the Updated Environment
from test_model.env_v6 import TradingEnvironment



# BEST_PARAMS = dict(
#     learning_rate = 0.006762264240246639,
#     n_steps = 64,
#     batch_size = 64,
#     gamma = 0.9963097260064849,
#     vf_coef = 0.3745639345817595,
#     clip_range = 0.390377340860396,
#     n_epochs = 4,
#     ent_coef = 0.07751906666033848,
# )

class TensorboardCallback(BaseCallback):
    """
    A callback that logs subgoal_success to tensorboard.

    This callback logs the subgoal_success metric from the info dictionary
    of each environment in each step to tensorboard.

    Args:
        max_ep_len (int): The maximum length of an episode.
        verbose (int, optional): The verbosity level: 0 for no output, 1 for info output, 2 for debug output. Defaults to 0.
    """

    def __init__(self, stats_window_size=1000, verbose=1):
        super(TensorboardCallback, self).__init__(verbose)
        self.stats_window_size = stats_window_size

        self.reward_buffer = deque(maxlen=stats_window_size)

        # average trading steps per episode (y-axis for even #) against steps (x-axis)
        self.step_buffer = deque(maxlen=stats_window_size)
        self.step_counter = 0
    def _on_step(self) -> bool:
        # Access the batched info dictionary from the most recent step
        # print(self.locals)
        infos = self.locals['infos']
        # Iterate over each environment's info dictionary
        for i, info in enumerate(infos):
            # print(info)
            reward = info['reward']
            shares = info['share']
            if info["done"]:
                IS = info['IS']
                IS_diff = info['IS_diff']
                IS_twap = info['IS_twap']
                self.logger.record(f"IS", IS)
                self.logger.record(f"IS_diff", IS_diff)
                self.logger.record(f"IS_twap", IS_twap)
                if len(self.step_buffer) >= self.stats_window_size:
                    self.step_buffer.popleft()
                self.step_buffer.append(info['time_elapsed'])

                mean_step_len = sum(self.step_buffer) / len(self.step_buffer)
                self.logger.record(f"steps",mean_step_len)

            if len(self.reward_buffer)>=self.stats_window_size:
                self.reward_buffer.popleft()
            self.reward_buffer.append(reward)

            if "time_slice" in info:
                time_slice = info["time_slice"]
                self.logger.record(f"time_slice", time_slice)
            # # Log reward metric to tensorboard
            reward = sum(self.reward_buffer) / len(self.reward_buffer)
            self.logger.record(f"mean_reward", reward)

            self.logger.record(f"shares", shares)

            # Calculate cummulative reward metric
            # cumm_reward = info.get('cumm_reward', 0)
            # Log cummulative metric to tensorboard

        return True

# class Model():
#     def __init__(self, model_dir, stats_window_size=1000, logging_dir="logs", n_env=1, wandb_logs=False):
        # self.model_dir = model_dir
        # os.makedirs(model_dir, exist_ok=True)
        # self.tensorboard_callback = TensorboardCallback(stats_window_size=stats_window_size)

        # self.n_env = n_env

        # self.wandb_callback = None
        # if wandb_logs:
        #     from wandb.integration.sb3 import WandbCallback
        #     self.wandb_callback = WandbCallback()

        # self.logging_dir = None
        # if logging_dir is not None:
        #     os.makedirs(logging_dir, exist_ok=True)
        #     self.logging_dir = logging_dir

    # def load_model(self, env, policy_kwargs, training_config = {}):
    #     # policy_kwargs['net_arch'] = dict(pi=[256, 256], vf=[256, 256])
    #     # multi_env = DummyVecEnv([env])
    #     # # training_config['use_sde'] = True
    #     # model_ = RecurrentPPO("MlpLstmPolicy", multi_env, policy_kwargs=policy_kwargs, tensorboard_log=self.logging_dir, **training_config)

    #     if self.n_env > 1:
    #         multi_env = SubprocVecEnv([env]*self.n_env)
    #     else:
    #         multi_env = DummyVecEnv([env])
    #     training_config = {"use_sde": False, 'verbose': 1, 'learning_rate': 0.0003}
    #     action_noise = NormalActionNoise(mean=np.zeros(multi_env.action_space.shape), sigma=0.1 * np.ones(multi_env.action_space.shape))
    #     training_config['action_noise'] = action_noise
    #     model_ = SAC("MlpPolicy", env=multi_env, tensorboard_log=self.logging_dir,  **training_config)
        
    #     return model_, multi_env
    
    # def get_model(self,data, env_params = {}, training_config = {}):
    #     def env():
    #         return TradingEnvironment(data,**env_params)

    #     model, vec_env = self.load_model(env, policy_kwargs={}, training_config = training_config)
    #     env_obj = env()
    #     return model, {'env' : env_obj, 'vec_env' : vec_env}
    
    # def train(self, data, resume=False, model_name="first.pt", env_params = {}, training_params={}, training_config = None, save=True):
    #     if training_config is None:
    #         training_config = BEST_PARAMS
    #     model, env = self.get_model(data, env_params=env_params,  training_config=training_config)        
    #     model_save_path = os.path.join(self.model_dir, model_name)
    #     print("Training model")
    #     if resume:
    #         if os.path.exists(model_save_path):
    #             # Load the model
    #             filepath = model_save_path
    #             model.policy.load_state_dict(torch.load(filepath))
    #             print(f"Model loaded from {filepath}")
    #         else:
    #             print(f"Model not found at {model_save_path}, training from scratch...")

    #     # Train the model
    #     if self.logging_dir is not None:
    #         if self.wandb_callback is not None:
    #             training_params['callback'] = CallbackList([self.tensorboard_callback, self.wandb_callback])
    #         else:
    #             training_params['callback'] = self.tensorboard_callback

    #     model.learn(reset_num_timesteps=resume, **training_params)
    #     if save:
    #         print("Saving model at " + model_save_path)
    #         self.save_model(model, model_save_path)

    #     env['vec_env'].close()
    #     return model

    # def save_model(self,model, filepath):
    #     # Save the model parameters
    #     torch.save(model.policy.state_dict(), filepath)
    #     # print(f"Model saved to {filepath}")

    # def test(self, data, model=None, env_params = {}, model_name="first.pt"):
    #     model_, env = self.get_model(data, env_params=env_params,training_config=BEST_PARAMS)
    #     if model is None:

    #         model_save_path = os.path.join(self.model_dir, model_name)
    #         # if resume:
    #         if os.path.exists(model_save_path):
    #             # Load the model
    #             filepath = model_save_path
    #             model_.policy.load_state_dict(torch.load(filepath, map_location = torch.device('cpu') if torch.cuda.is_available() == False else torch.device('cuda')))
    #             print(f"Model loaded from {filepath}")
    #         else:
    #             raise Exception(f"Model not found at {model_save_path}")
    #             # print(f"Model not found at {model_save_path}, training from scratch...")
    #         model = model_

    #     env_ = env['env']
    #     obs = env_.reset(randomize=False)
    #     num_envs = 1
    #     # episode_starts = np.ones((num_envs,), dtype=bool)
    #     total_reward = 0
    #     done = False
    #     _states = None
    #     with torch.no_grad():
    #         while not done:
    #             action, _states = model.predict(obs, state=_states, deterministic=True)
    #             # print(action, _states[0].sum()) 
    #             obs, rewards, done, info = env_.step(action)
    #             # episode_starts[0] = done
    #             # print(episode_starts, _states[0].sum())
    #             total_reward += rewards

    #     env['vec_env'].close()
    #     trades = pd.DataFrame(env_.trades_info)
    #     trades = trades[trades['shares'] != 0.0]
    #     return total_reward, trades
    
    # def fine_tuning_model(self, config):
    #     train_data = config['train_data']
    #     training_config = {}
    #     training_config['learning_rate'] = config['learning_rate']
    #     training_config['n_steps'] = config['n_steps']
    #     training_config['batch_size'] = config['batch_size']
    #     training_config['gamma'] = config['gamma']
    #     training_config['clip_range'] = config['clip_range']
    #     training_config['n_epochs'] = config['n_epochs']
    #     training_config['ent_coef'] = config['ent_coef']
    #     resume = config['resume']

    #     training_params = {}
    #     training_params["total_timesteps"] = config['total_timesteps']
    #     training_params["callback"] = config['callback']

    #     test_data = config['test_data']
    #     model =self.train(train_data , training_config=training_config, resume=resume, training_params=training_params, env_params=config['env_params'], save=False)

    #     rew, trades = self.test(test_data, model, env_params=config['env_params'])

    #     train.report({"reward":rew})

    #     return 

#-----------------------------------------------------------------------------------------------------------------------------
# RL Model 5 Integration Code Starts from here
from datetime import datetime
import pytz
from GordonRitter.utils.pipeline import OptimalBetSizeInference
class RLModel5:
    def __init__(self,model_dir,data_dir):
        self.model_dir = model_dir
        self.grModel = OptimalBetSizeInference(data_dir = data_dir)
    def test(self,processed_data,ticker,end_timestamp,timeframe,inventory,bet_sz_model_dir = "Models/bet_sizing_v1",backtest=True):
        rs = self.grModel.run_pipeline(
                        data = processed_data ,
                        ticker=ticker,
                        end_timestamp=datetime.now(pytz.UTC).strftime('%Y-%m-%d'),
                        timeframe=390,
                        inventory=10000,
                        bet_sz_model_dir='Models/bet_sizing_v1',
                        backtest=True)
        return rs

#-----------------------------------------------------------------------------------------------------------------


        



        