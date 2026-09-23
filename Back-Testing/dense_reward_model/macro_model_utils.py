"""
Additional model function for testing, saving models.
"""
import os
import pandas as pd
import numpy as np

import torch
from stable_baselines3 import PPO
from gym import spaces
from ray import tune
import ray

# from utils.macro_model import PPO_MODEL_BEST_PARAMS, MetaLearner
# from utils.macro_model import CustomTransformerPolicy, MetaLearner, PPO_MODEL_BEST_PARAMS, TabActorCriticPolicy, TabTransformerPolicy, \
#     PPO_MODEL_BEST_PARAMS_TAB
from test_model.env import TradingEnvironment#, CustomTradingEnvironment, TradingEnvironmentMacroV2, TradingEnvironmentNew, TradingEnvironment_v6
from test_model.env_dense_reward import TradingEnvironmentMacroV3

from test_model.data_handler import InferenceDataHandler#, TechnicalIndicators
from test_model.fetch_merge_data import fetch_and_merge_data
# import pytz
# from icecream import ic
from stable_baselines3 import SAC

PPO_MODEL_BEST_PARAMS_TAB = {
    "learning_rate": 0.0003,
    "n_steps": 2048,
    "batch_size": 64,
    "n_epochs": 10,
    "gamma": 0.99,
    "gae_lambda": 0.95,
    "clip_range": 0.2,
    "ent_coef": 0.0,
    "vf_coef": 0.5,
    "max_grad_norm": 0.5,
    "use_sde": False,
    "sde_sample_freq": -1,
    "target_kl": None,
}
PPO_MODEL_BEST_PARAMS = {
    "learning_rate": 0.0003,
    "n_steps": 2048,
    "batch_size": 64,
    "n_epochs": 10,
    "gamma": 0.99,
    "gae_lambda": 0.95,
    "clip_range": 0.2,
    "ent_coef": 0.0,
    "vf_coef": 0.5,
    "max_grad_norm": 0.5,
    "use_sde": False,
    "sde_sample_freq": -1,
    "target_kl": None,
}

class MacroTraderModel:
    """
    This class is responsible for training, saving, and loading models for different trading scenarios. 
    Each method in the class loads a model configured with specific hyperparameters and action spaces 
    based on the trading scenario (small, small-medium, medium, medium-large, large).
    """

    def __init__(self, model_dir='Models'):
        """
        Initializes the Model class.
        """
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)

    def _load_model(self, env, filepath, policy_kwargs, training_config=PPO_MODEL_BEST_PARAMS_TAB):
        """
        Loads a PPO model with a custom transformer policy.
        
        Args:
        - env (gym.Env): The trading environment for the model.
        - filepath (str): The file path to the saved model parameters.
        - policy_kwargs (dict): Additional keyword arguments for configuring the policy.
        - best_hyperparameters (dict): The best hyperparameters used for training the PPO model.

        Returns:
        - model (PPO): The loaded PPO model configured with the given environment and hyperparameters.
        """
        model = PPO(CustomTransformerPolicy, env, policy_kwargs=policy_kwargs, **training_config)
        #

        # policy_kwargs['state_cols'] = env.state_columns
        # model = PPO(TabTransformerPolicy, env, policy_kwargs=policy_kwargs, **training_config)

        # model.policy.load_state_dict(torch.load(filepath))
        # print(f"Model loaded from {filepath}")

        return model

    def _load_tabtransformer_model(self, env, filepath, policy_kwargs, training_config=PPO_MODEL_BEST_PARAMS_TAB):
        """
        Loads a PPO model with a tabtransformer policy.

        Args:
        - env (gym.Env): The trading environment for the model.
        - filepath (str): The file path to the saved model parameters.
        - policy_kwargs (dict): Additional keyword arguments for configuring the policy.
        - best_hyperparameters (dict): The best hyperparameters used for training the PPO model.

        Returns:
        - model (PPO): The loaded PPO model configured with the given environment and hyperparameters.
        """
        policy_kwargs['continuous_cols'] = env.state_columns_all_data
        policy_kwargs['squash_output'] = True

        # policy_kwargs['lr_schedule'] = None
        # policy_kwargs['share_features_extractor'] = False
        model = PPO(TabActorCriticPolicy, env, policy_kwargs=policy_kwargs, **training_config)


        # model  = SAC(TabActorCriticPolicy, env, verbose=1)
        return model

    def get_model(self, data, market_cap, scenario, training_config=PPO_MODEL_BEST_PARAMS):
        """
        Retrieves a Pre-trained MacroTrader Model based on the specified market capitalization and scenario.

        Args:
        - data: The input data used for training the model.
        - market_cap (str): The market capitalization of the model to retrieve. Can be 'small', 'medium', or 'large'.
        - scenario (str): The scenario of the model to retrieve.

        Returns:
        - model_: The retrieved trained model.

        Raises:
        - ValueError: If the model is not found at the specified save path.
        """

        if market_cap == 'small':
            model_, env_, model_save_path = self._get_small_cap_model(data, scenario=scenario,
                                                                      training_config=training_config)
        elif market_cap == 'medium':
            model_, env_, model_save_path = self._get_medium_cap_model(data, scenario=scenario,
                                                                       training_config=training_config)
        else:
            model_, env_, model_save_path = self._get_large_cap_model(data, scenario=scenario,
                                                                      training_config=training_config)
        if not os.path.exists(model_save_path):
            raise ValueError(f"Model not found at {model_save_path}")

        model_.policy.load_state_dict(torch.load(model_save_path))

        return model_

    def _get_large_cap_model(self, data, train_data_raw, scenario, preferred_timeframe, get_tab_transformer=False,
                             training_config=PPO_MODEL_BEST_PARAMS):
        """
        Retrieves the large cap model based on the given scenario.

        Args:
            data: The historical market data.
            scenario (str): The scenario to select the model.

        Returns:
            tuple: A tuple containing the model, environment, and file path.
        """

        if scenario == 'large':
            print('large cap, large scenario model selected')
            file_path = f'{self.model_dir}/model_large_cap_large_timeframe.h5'
            model, env = self._get_large(data, train_data_raw, file_path, market_cap='large', preferred_timeframe=preferred_timeframe,
                                         get_tab_transformer=get_tab_transformer,
                                         training_config=training_config)
        elif scenario == 'medium-large':
            print('large cap, medium-large scenario model selected')
            file_path = f'{self.model_dir}/model_large_cap_medium_large_timeframe.h5'
            model, env = self._get_medium_large(data, file_path, market_cap='large',
                                                preferred_timeframe=preferred_timeframe,
                                                get_tab_transformer=get_tab_transformer,
                                                training_config=training_config)
        elif scenario == 'medium':
            print('large cap, medium scenario model selected')
            file_path = f'{self.model_dir}/model_large_cap_medium_timeframe.h5'
            model, env = self._get_medium(data, file_path, market_cap='large', preferred_timeframe=preferred_timeframe,
                                          get_tab_transformer=get_tab_transformer,
                                          training_config=training_config)
        elif scenario == 'small-medium':
            print('large cap, small-medium scenario model selected')
            file_path = f'{self.model_dir}/model_large_cap_small_medium_timeframe.h5'
            model, env = self._get_small_medium(data, file_path, market_cap='large',
                                                preferred_timeframe=preferred_timeframe,
                                                get_tab_transformer=get_tab_transformer,
                                                training_config=training_config)
        elif scenario == 'small':
            print('large cap, small scenario model selected')
            file_path = f'{self.model_dir}/tab_model_large_cap_small_timeframe.h5'
            model, env = self._get_small(data, file_path, market_cap='large', preferred_timeframe=preferred_timeframe,
                                         get_tab_transformer=get_tab_transformer,
                                         training_config=training_config)
        else:
            print('large cap, large scenario model selected')
            file_path = f'{self.model_dir}/tab_model_large_cap_large_timeframe.h5'
            model, env = self._get_large(data, file_path, market_cap='large', preferred_timeframe=preferred_timeframe,
                                         get_tab_transformer=get_tab_transformer,
                                         training_config=training_config)
        return model, env, file_path

    def _get_medium_cap_model(self, data, scenario, preferred_timeframe, get_tab_transformer=False,
                              training_config=PPO_MODEL_BEST_PARAMS):
        """
        Retrieves a medium-cap model based on the provided data and scenario.

        Args:
            data: The data to be used in the model.
            scenario (str): The scenario for which the model is to be retrieved.

        Returns:
            tuple: A tuple containing the model, environment, and file path.
        """

        if scenario == 'large':
            print('Medium cap, large scenario model selected')
            file_path = f'{self.model_dir}/model_medium_cap_large_timeframe.h5'
            model, env = self._get_large(data, file_path, market_cap='medium', preferred_timeframe=preferred_timeframe,
                                         get_tab_transformer=get_tab_transformer,
                                         training_config=training_config)
        elif scenario == 'medium-large':
            print('Medium cap, medium-large scenario model selected')
            file_path = f'{self.model_dir}/model_medium_cap_medium_large_timeframe.h5'
            model, env = self._get_medium_large(data, file_path, market_cap='medium',
                                                preferred_timeframe=preferred_timeframe,
                                                get_tab_transformer=get_tab_transformer,
                                                training_config=training_config)
        elif scenario == 'medium':
            print('Medium cap, medium scenario model selected')
            file_path = f'{self.model_dir}/model_medium_cap_medium_timeframe.h5'
            model, env = self._get_medium(data, file_path, market_cap='medium', preferred_timeframe=preferred_timeframe,
                                          get_tab_transformer=get_tab_transformer,
                                          training_config=training_config)
        elif scenario == 'small-medium':
            print('Medium cap, small-medium scenario model selected')
            file_path = f'{self.model_dir}/model_medium_cap_small_medium_timeframe.h5'
            model, env = self._get_small_medium(data, file_path, market_cap='medium',
                                                preferred_timeframe=preferred_timeframe,
                                                get_tab_transformer=get_tab_transformer,
                                                training_config=training_config)
        elif scenario == 'small':
            print('Medium cap, small scenario model selected')
            file_path = f'{self.model_dir}/model_medium_cap_small_timeframe.h5'
            model, env = self._get_small(data, file_path, market_cap='medium', preferred_timeframe=preferred_timeframe,
                                         get_tab_transformer=get_tab_transformer,
                                         training_config=training_config)
        else:
            print('Medium cap, large scenario model selected')
            file_path = f'{self.model_dir}/model_medium_cap_large_timeframe.h5'
            model, env = self._get_large(data, file_path, market_cap='medium', preferred_timeframe=preferred_timeframe,
                                         get_tab_transformer=get_tab_transformer,
                                         training_config=training_config)
        return model, env, file_path

    def _get_small_cap_model(self, data, scenario, preferred_timeframe, get_tab_transformer=False,
                             training_config=PPO_MODEL_BEST_PARAMS):
        """
        Retrieves the small cap model based on the given scenario.

        Args:
            data (pd.DataFrame): The historical market data.
            scenario (str): The scenario to select the model.

        Returns:
            tuple: A tuple containing the model, environment, and file path.
        """

        if scenario == 'large':
            print('Small cap, large scenario model selected')
            file_path = f'{self.model_dir}/model_small_cap_large_timeframe.h5'
            model, env = self._get_large(data, file_path, market_cap='small', preferred_timeframe=preferred_timeframe,
                                         get_tab_transformer=get_tab_transformer,
                                         training_config=training_config)
        elif scenario == 'medium-large':
            print('Small cap, medium-large scenario model selected')
            file_path = f'{self.model_dir}/model_small_cap_medium_large_timeframe.h5'
            model, env = self._get_medium_large(data, file_path, market_cap='small',
                                                get_tab_transformer=get_tab_transformer,
                                                training_config=training_config,
                                                preferred_timeframe=preferred_timeframe)
        elif scenario == 'medium':
            print('Small cap, medium scenario model selected')
            file_path = f'{self.model_dir}/model_small_cap_medium_timeframe.h5'
            model, env = self._get_medium(data, file_path, market_cap='small', preferred_timeframe=preferred_timeframe,
                                          get_tab_transformer=get_tab_transformer,
                                          training_config=training_config)
        elif scenario == 'small-medium':
            print('Small cap, small-medium scenario model selected')
            file_path = f'{self.model_dir}/model_small_cap_small_medium_timeframe.h5'
            model, env = self._get_small_medium(data, file_path, market_cap='small',
                                                preferred_timeframe=preferred_timeframe,
                                                get_tab_transformer=get_tab_transformer,
                                                training_config=training_config)
        elif scenario == 'small':
            print('Small cap, small scenario model selected')
            file_path = f'{self.model_dir}/model_small_cap_small_timeframe.h5'
            model, env = self._get_small(data, file_path, market_cap='small', preferred_timeframe=preferred_timeframe,
                                         get_tab_transformer=get_tab_transformer,
                                         training_config=training_config)
        else:
            print('Small cap, large scenario model selected')
            file_path = f'{self.model_dir}/model_small_cap_large_timeframe.h5'
            model, env = self._get_large(data, file_path, market_cap='small', preferred_timeframe=preferred_timeframe,
                                         get_tab_transformer=get_tab_transformer,
                                         training_config=training_config)
        return model, env, file_path

    def _get_small(self, data, file_path, preferred_timeframe, market_cap='large', get_tab_transformer=False,
                   training_config=PPO_MODEL_BEST_PARAMS):
        """
        Configures and returns a PPO model for small trade scenarios.

        Args:
        - data (pd.DataFrame): Historical market data to be used in the trading environment - 1 row.

        Returns:
        - model (PPO): The PPO model configured for small trade scenarios.
        """
        # file_path = f'{self.model_dir}/model_small.h5'
        initial_inventory = 10

        original_action_space = spaces.Box(low=np.array([0.2, 20]), high=np.array([0.66, 30]), dtype=np.float32)
        action_space = spaces.Box(low=np.array([-1, -1]), high=np.array([1, 1]), dtype=np.float32)

        env = TradingEnvironmentMacroV2(data, action_space, original_action_space,
                                        preferred_timeframe=preferred_timeframe,
                                        initial_inventory=initial_inventory, scenario='large')

        scenario = 'small'
        if not get_tab_transformer:
            model = self._load_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap},
                                     training_config=training_config)
        else:
            model = self._load_tabtransformer_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap},
                                                    training_config=training_config)
        return model, env

    def _get_small_medium(self, data, file_path, preferred_timeframe, market_cap='large', get_tab_transformer=False,
                          training_config=PPO_MODEL_BEST_PARAMS):
        """
        Configures and returns a PPO model for small to medium trade scenarios.

        Args:
        - data (pd.DataFrame): Historical market data to be used in the trading environmen - 1 row.

        Returns:
        - model (PPO): The PPO model configured for small to medium trade scenarios.
        """
        # file_path = 'Models/model_small_med.h5'
        initial_inventory = 100
        original_action_space = spaces.Box(low=np.array([0.2, 20]), high=np.array([0.66, 30]), dtype=np.float32)
        action_space = spaces.Box(low=np.array([-1, -1]), high=np.array([1, 1]), dtype=np.float32)

        env = TradingEnvironmentMacroV2(data, action_space, original_action_space,
                                        preferred_timeframe=preferred_timeframe,
                                        initial_inventory=initial_inventory, scenario='large')
        scenario = 'small-medium'
        if not get_tab_transformer:
            model = self._load_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap},
                                     training_config=training_config)
        else:
            model = self._load_tabtransformer_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap},
                                                    training_config=training_config)
        return model, env

    def _get_medium(self, data, file_path, preferred_timeframe, market_cap='large', get_tab_transformer=False,
                    training_config=PPO_MODEL_BEST_PARAMS):
        """
        Configures and returns a PPO model for medium trade scenarios.

        Args:
        - data (pd.DataFrame): Historical market data to be used in the trading environment - 1 row.

        Returns:
        - model (PPO): The PPO model configured for medium trade scenarios.
        """
        # file_path = 'Models/model_med.h5'
        initial_inventory = 500
        original_action_space = spaces.Box(low=np.array([0.20, 30]), high=np.array([0.50, 50]), dtype=np.float32)
        action_space = spaces.Box(low=np.array([-1, -1]), high=np.array([1, 1]), dtype=np.float32)

        env = TradingEnvironmentMacroV2(data, action_space, original_action_space,
                                        preferred_timeframe=preferred_timeframe,
                                        initial_inventory=initial_inventory, scenario='large')
        scenario = 'medium'
        if not get_tab_transformer:
            model = self._load_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap},
                                     training_config=training_config)
        else:
            model = self._load_tabtransformer_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap},
                                                    training_config=training_config)
        return model, env

    def _get_medium_large(self, data, file_path, preferred_timeframe, market_cap='large', get_tab_transformer=False,
                          training_config=PPO_MODEL_BEST_PARAMS):
        """
        Configures and returns a PPO model for medium to large trade scenarios.

        Args:
        - data (pd.DataFrame): Historical market data to be used in the trading environment - 1 row.

        Returns:
        - model (PPO): The PPO model configured for medium to large trade scenarios.
        """
        # file_path = 'Models/model_med_lg.h5'
        initial_inventory = 2000
        original_action_space = spaces.Box(low=np.array([0.10, 30]), high=np.array([0.40, 50]), dtype=np.float32)
        action_space = spaces.Box(low=np.array([-1, -1]), high=np.array([1, 1]), dtype=np.float32)

        env = TradingEnvironmentMacroV2(data, action_space, original_action_space,
                                        preferred_timeframe=preferred_timeframe,
                                        initial_inventory=initial_inventory, scenario='large')

        scenario = 'medium-large'
        best_hyperparameters = {'learning_rate': 0.0009931989008886031, 'n_steps': 512, 'batch_size': 128,
                                'gamma': 0.9916829193042708, 'clip_range': 0.21127653449387027, 'n_epochs': 6,
                                'ent_coef': 0.1}
        if not get_tab_transformer:
            model = self._load_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap},
                                     training_config=training_config)
        else:
            model = self._load_tabtransformer_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap},
                                                    training_config=training_config)
        return model, env

    def _get_large(self, data, train_data_raw, file_path, preferred_timeframe, market_cap='large', get_tab_transformer=False,
                   training_config=PPO_MODEL_BEST_PARAMS):
        """
        Configures and returns a PPO model for large trade scenarios.

        Args:
        - data (pd.DataFrame): Historical market data to be used in the trading environment - 1 row.

        Returns:
        - model (PPO): The PPO model configured for large trade scenarios.
        """
        # file_path = 'Models/model_lg_cap_.h5'
        initial_inventory = 10000
        original_action_space = spaces.Box(low=np.array([0.01, 30]), high=np.array([0.33, 30]), dtype=np.float32)
        action_space = spaces.Box(low=np.array([-1, -1]), high=np.array([1, 1]), dtype=np.float32)

        action_space = spaces.Box(low=np.array([0]), high=np.array([60]), dtype=np.float32)
        original_action_space = spaces.Box(low=np.array([0.001]), high=np.array([0.8]), dtype=np.float32)


        env = TradingEnvironmentMacroV2(data, train_data_raw, action_space, original_action_space,
                                        preferred_timeframe=preferred_timeframe,
                                        initial_inventory=initial_inventory, scenario='large')
        scenario = 'large'
        best_hyperparameters = {'learning_rate': 0.0009931989008886031, 'n_steps': 512, 'batch_size': 128,
                                'gamma': 0.9916829193042708, 'clip_range': 0.21127653449387027, 'n_epochs': 6,
                                'ent_coef': 0.1}
        if not get_tab_transformer:
            model = self._load_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap},
                                     training_config=training_config)
        else:
            model = self._load_tabtransformer_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap},
                                                    training_config=training_config)
        return model, env

    def train(self, data, train_data_raw, five_level_data, preferred_timeframe, scenario='medium', market_cap="large", get_tab_transformer=False,
              training_config=PPO_MODEL_BEST_PARAMS, resume=False,
              training_params={}, use_new_env = False):
        """
        Trains a MacroTrader model based on the provided data, scenario, market capitalization, and training configuration.

        Args: data: The input data used for training the model. scenario (str): The scenario of the model to train.
        Defaults to 'medium'. market_cap (str): The market capitalization of the model to train. Can be 'small',
        'medium', or 'large'. Defaults to 'large'. total_timesteps (int): The total number of timesteps to train the
        model for. Defaults to 10000. training_config (dict): The training configuration for the model. Defaults to
        PPO_MODEL_BEST_PARAMS, can be used for tuning hyperparameters. resume (bool): Whether to resume training from
        a saved model. Defaults to False. training_params (dict): Additional training parameters used in model.learn
        method. Defaults to {}.

        Returns:
            None
        """

        model_save_path = 'acmr_model'


        if use_new_env:
            env_ = TradingEnvironment_v6(train_data_raw, 30000, 390)

        env_ = TradingEnvironmentMacroV3(data, train_data_raw, five_level_data, eval=False, preferred_timeframe=80, initial_inventory=30000)


        policy_kwargs = dict(share_features_extractor = False)
        # "action_noise": NormalActionNoise(mean=np.array([0]), sigma=np.array([10]))}
        training_params = {"total_timesteps" : 100000}
        training_config = {"use_sde": False, 'verbose': 2, 'learning_rate': 0.0001}
        model_ = SAC("MlpPolicy", env=env_, policy_kwargs = policy_kwargs, **training_config)

        model_.learn(**training_params)
        self.save_model(model_, model_save_path)
        return model_, env_

    def test(self, data, preferred_timeframe, env=None, model=None, market_cap="large", scenario="medium",
             get_tab_transformer=False):

        if market_cap == "large":
            model_, env_, model_save_path = self._get_large_cap_model(data, scenario,
                                                                      preferred_timeframe=preferred_timeframe,
                                                                      get_tab_transformer=get_tab_transformer)
        elif market_cap == "medium":
            model_, env_, model_save_path = self._get_medium_cap_model(data, scenario,
                                                                       preferred_timeframe=preferred_timeframe,
                                                                       get_tab_transformer=get_tab_transformer)
        elif market_cap == "small":
            model_, env_, model_save_path = self._get_small_cap_model(data, scenario,
                                                                      preferred_timeframe=preferred_timeframe,
                                                                      get_tab_transformer=get_tab_transformer)
        else:
            model_, env_, model_save_path = self._get_large_cap_model(data, scenario,
                                                                      preferred_timeframe=preferred_timeframe,
                                                                      get_tab_transformer=get_tab_transformer)
        if not os.path.exists(model_save_path):
            pass

        env_.eval = True

        print(model_save_path)
        if model is None:
            model_.policy.load_state_dict(torch.load(model_save_path))
            model = model_

        obs = env_.reset()
        cum_reward = 0
        for _ in range(len(data)):
            action, _states = model.predict(obs, deterministic=True)
            obs, rewards, done, info = env_.step(action)
            cum_reward += rewards
            if done:
                break
        return cum_reward, env_

    def test_benchmark(self, data, data_raw,  five_level_data, preferred_timeframe, model=None, market_cap="large", scenario="large",
                       get_tab_transformer=False, use_new_env = False):

        file_path = f'{self.model_dir}/model_large_cap_large_timeframe.h5'
        file_path = 'test_model/dense_reward_model'
        if use_new_env:
            env = TradingEnvironment_v6(data, 10000, 390)

        env = TradingEnvironmentMacroV3(data, data_raw, five_level_data, eval=True,
                                        preferred_timeframe=390, initial_inventory=10000)


        if get_tab_transformer:
            training_config = PPO_MODEL_BEST_PARAMS_TAB
            policy_kwargs = {'scenario': scenario, 'market_cap': market_cap}
            model = SAC.load(file_path, env)



        def display_action_categorical_distribution(obs, model):
            """
            Display the action probability distribution for debugging.

            :param obs: Current observation
            :param model: Trained model
            """
            dist = model.policy.get_distribution(model.policy.obs_to_tensor(obs)[0])

            print(dist.distribution.loc.cpu().numpy())
            print(dist.distribution.scale.cpu().numpy())

            # print(torch.nn.Softmax().forward(input = dist.distribution[0].logits))

                         
        action_lst = []
        infos = []
        rewards = []
        with torch.no_grad():
            display_action_probs_debugging = True
            obs = env.reset()
            cum_reward = 0
            for _ in range(len(data)):
                action, _states = model.predict(obs, deterministic=True)
                
                obs, reward, done, info = env.step(action)
                
                rewards.append(reward)
                infos.append(info)
                cum_reward += reward
                action_lst.append(action)

                if done:
                    break
        return cum_reward, env, model, infos

    def test_benchmark_twap(self, data, data_raw, five_level_data, preferred_timeframe, model=None, market_cap="large",
                       scenario="large",
                       get_tab_transformer=False, use_new_env=False):


        file_path = f'{self.model_dir}/model_large_cap_large_timeframe.h5'
        file_path = 'acmr_model'
        if use_new_env:
            env = TradingEnvironment_v6(data, 10000, 390)

        env = TradingEnvironmentMacroTWAPTest(data, data_raw, five_level_data, eval=True,
                                        preferred_timeframe=80, initial_inventory=30000)

        if get_tab_transformer:
            training_config = PPO_MODEL_BEST_PARAMS_TAB
            policy_kwargs = {'scenario': scenario, 'market_cap': market_cap}
            model = SAC.load(file_path, env)


        action_lst = []
        infos = []
        rewards = []
        with torch.no_grad():
            display_action_probs_debugging = True
            obs = env.reset()
            cum_reward = 0
            for _ in range(len(data)):
                action, _states = model.predict(obs, deterministic=True)

                obs, reward, done, info = env.step(action)
                rewards.append(reward)
                infos.append(info)
                cum_reward += reward
                action_lst.append(action)

                if done:
                    break
        return cum_reward, env, model, infos

    def save_model(self, model, filepath):
        # Save the model parameters
        # torch.save(model.policy.state_dict(), filepath)
        model.save(filepath)
        print(f"Model saved to {filepath}")

    def fine_tuning_model(self, config):
        train_data = config['train_data']
        train_data_raw = config['train_data_raw']
        market_cap = config['market_cap']
        scenario = config['scenario']
        training_config = {}
        training_config['learning_rate'] = config['learning_rate']
        training_config['n_steps'] = config['n_steps']
        training_config['batch_size'] = config['batch_size']
        training_config['gamma'] = config['gamma']
        training_config['clip_range'] = config['clip_range']
        training_config['n_epochs'] = config['n_epochs']
        training_config['ent_coef'] = config['ent_coef']
        resume = config['resume']

        training_params = {}
        training_params["total_timesteps"] = config['total_timesteps']
        training_params["callback"] = config['callback']

        test_data = config['test_data']
        preferred_timeframe = 200
        modeltab, env_ = self.train(train_data, train_data_raw, preferred_timeframe=390,
                                            market_cap=market_cap,
                                            scenario=scenario, get_tab_transformer=True, resume=False,
                                            training_params=training_params,
                                            training_config=training_config)
        if scenario == 'large':
            preferred_timeframe = 390
            initial_inventory = 10000
            action_space = spaces.Box(low=np.array([0.05, 30]), high=np.array([0.33, 50]), dtype=np.float32)
        elif scenario == 'medium-large':
            preferred_timeframe = 390
            initial_inventory = 2000
            action_space = spaces.Box(low=np.array([0.10, 30]), high=np.array([0.40, 50]), dtype=np.float32)
        elif scenario == 'medium':
            preferred_timeframe = 390
            initial_inventory = 500
            action_space = spaces.Box(low=np.array([0.20, 30]), high=np.array([0.50, 50]), dtype=np.float32)
        elif scenario == 'small-medium':
            preferred_timeframe = 390
            initial_inventory = 10
            action_space = spaces.Box(low=np.array([0.2, 20]), high=np.array([0.66, 30]), dtype=np.float32)
        elif scenario == 'small':
            preferred_timeframe = 390
            initial_inventory = 10
            action_space = spaces.Box(low=np.array([0.33, 30]), high=np.array([1, 50]), dtype=np.float32)
        else:
            pass

        # action_space = spaces.Box(low=np.array([-1, -1]), high=np.array([1, 1]), dtype=np.float32)
        #
        # rew, tenv = self.test(test_data, preferred_timeframe=preferred_timeframe, model=model, market_cap=market_cap,
        #                       scenario=scenario)
        #
        # our_trades = pd.DataFrame(tenv.trades)

        # ray.train.report({"test_slippage": our_trades['slippage'].sum()})

        ray.train.report({"train_cum_reward": env_.cumulative_reward})

        return

    def get_schedule(self, model, timeframe, transaction_size, input_row, data, inference_data_class, meta):
        """
        Generates a trading schedule based on the transaction size and input data.

        Args:
        - timeframe (int): The timeframe for trade execution.
        - transaction_size (int): The size of the transaction.
        - input_row (pd.DataFrame): The input data row with forecasts and technical indicators.

        Returns:
        - list: A list of trades executed based on the generated schedule.
        """
        print("LOGGING: Generating Schedule...")

        def infer_macro(timeframe, transaction_size, input_data, data):
            print(f"Input Data: {input_data}")
            scenario = meta.classify_scenario(transaction_size, timeframe)
            print(f"Scenario: {scenario}")

            action_space = spaces.Box(low=np.array([0.10, 30]), high=np.array([0.40, 50]), dtype=np.float32)
            print('--------Input data: ', input_data)
            env = CustomTradingEnvironment(input_data, scenario, action_space, preferred_timeframe=timeframe,
                                           initial_inventory=transaction_size)
            obs = env.reset()
            obs = obs.astype(np.float32)
            done = False
            forecast_step = 0
            observations = []
            state_cols = ['open', 'high', 'low', 'close', 'volume', 'RSI', 'MACD', 'MACD_signal', 'MACD_hist',
                          'Stoch_k', 'Stoch_d', 'OBV', 'Upper_BB', 'Middle_BB', 'Lower_BB', 'ATR_1', 'ADX',
                          '+DI', '-DI', 'CCI', 'transaction_cost', 'forecast_6Hr_open', 'forecast_6Hr_close',
                          'forecast_6Hr_high', 'forecast_6Hr_low', 'forecast_6Hr_volatility',
                          'forecast_6Hr_volume', 'forecast_6Hr_transaction_cost']

            while not done:
                action, _states = model.predict(obs)
                step = int(np.ceil(action[1]))
                forecast_step += step
                obs = inference_data_class.add_real_time_forecasts(data, forecast_step)
                obs = obs.squeeze()
                print(obs)
                observations.append(obs)
                obs = obs[state_cols]
                done, info = env.step(action)

                if done:
                    break

            micro_input = pd.DataFrame(observations)
            trades = env.render()
            print(trades)
            return trades, micro_input

        trades, micro_input = infer_macro(timeframe, transaction_size, input_row, data)
        return trades, micro_input

    def run_pipeline(self, model):
        """
        Runs the entire pipeline for the trading model, including data retrieval,
        technical indicator addition, forecasting, and generating trade schedules.

        Returns:
        - list: The list of trades generated by the model.
        """
        timeframe = 390
        inventory = 1000
        transaction_size = 99
        meta = MetaLearner()
        inference_data_class = InferenceDataHandler()
        data_dir = 'Data'
        # Define the start and end dates
        start_time = '2024-07-01'
        end_time = '2024-08-16'
        ticker = "AAPL"
        inference_data_class = InferenceDataHandler()
        #
        df = fetch_and_merge_data(ticker, start_time, end_time)
        tI = TechnicalIndicators(df)

        # # Convert the datetime column to UTC first (if it isn't already)
        # df['datetime'] = pd.to_datetime(df['datetime'], utc=True)
        #
        # # Define the Eastern Time (ET) timezone
        # et_timezone = pytz.timezone('America/New_York')
        #
        # # Convert the datetime column to ET and format it
        # df['datetime'] = df['datetime'].dt.tz_convert(et_timezone)
        # df['datetime'] = df['datetime'].dt.strftime('%Y-%m-%d %H:%M:%S')
        data = tI.add_all_indicators()

        input_row = inference_data_class.add_forecasts(data)

        trades, micro_inputs = self.get_schedule(model, timeframe, transaction_size, input_row, data,
                                                 inference_data_class, meta)
        micro_inputs.to_csv("micro_input_1.csv", index=False)

        print(micro_inputs)
        print(trades)

        flattened_data = []
        for entry in trades:
            flattened_entry = {
                'timestamp': entry['timestamp'],
                'action_1': entry['action'][0],
                'action_2': entry['action'][1],
                'shares': entry['shares'],
                'inventory': entry['inventory'],
                'time left': entry['time left'],
                'vwap': entry['vwap']

            }
            flattened_data.append(flattened_entry)

        # Save to CSV
        data_df = pd.DataFrame(flattened_data)

        final_micro_inputs = pd.read_csv('micro_input_1.csv')
        final_micro_inputs['shares'] = data_df['shares']
        final_micro_inputs['vwap'] = data_df['vwap']

        final_micro_inputs.to_csv('final_micro_input.csv')
        return final_micro_inputs
