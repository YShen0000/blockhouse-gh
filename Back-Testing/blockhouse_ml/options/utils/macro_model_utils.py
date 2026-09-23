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
from stable_baselines3.common.vec_env import SubprocVecEnv, DummyVecEnv
import gc

from blockhouse_ml.options.utils.macro_model import PPO_MODEL_BEST_PARAMS, MetaLearner
from blockhouse_ml.options.utils.macro_model import CustomTransformerPolicy, MetaLearner, PPO_MODEL_BEST_PARAMS, PPO_MODEL_BEST_PARAMS_TAB, TabTransformerPolicy
from blockhouse_ml.options.utils.env import TradingEnvironment
from blockhouse_ml.options.utils.data_handler import InferenceDataHandler


class MacroTraderModel:
    """
    This class is responsible for training, saving, and loading models for different trading scenarios. 
    Each method in the class loads a model configured with specific hyperparameters and action spaces 
    based on the trading scenario (small, small-medium, medium, medium-large, large).
    """

    def __init__(self, model_dir = 'Models', num_envs = 1):
        """
        Initializes the Model class.
        """
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)

        # Number of parallel environments for training
        self.num_envs = num_envs

        # Will keep the track of the training environment, and will be used for closing and cleaning up the environment
        self.multi_env = None

        
    def _load_model(self, env, filepath, policy_kwargs, training_config = PPO_MODEL_BEST_PARAMS):
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

        if self.num_envs > 1:
            multi_env = SubprocVecEnv([env for _ in range(self.num_envs)])
        else:
            multi_env = DummyVecEnv([env])
        model = PPO(CustomTransformerPolicy, multi_env, policy_kwargs=policy_kwargs, **training_config)
        # model.policy.load_state_dict(torch.load(filepath))
        # print(f"Model loaded from {filepath}")
        self.multi_env = multi_env

        return model

    def _load_tabtransformer_model(self, env, filepath, policy_kwargs, training_config = PPO_MODEL_BEST_PARAMS):
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
        print(f"Initializing TabTransformer Model")
        training_config=PPO_MODEL_BEST_PARAMS_TAB
        if self.num_envs > 1:
            multi_env = SubprocVecEnv([env for _ in range(self.num_envs)])
        else:
            multi_env = DummyVecEnv([env])
        print(f"Total Envs for training: {self.num_envs}")
        self.multi_env = multi_env
        model = PPO(TabTransformerPolicy, multi_env, policy_kwargs=policy_kwargs, **training_config)

        return model

    
    def get_model(self, data, market_cap, scenario, training_config = PPO_MODEL_BEST_PARAMS,  get_tab_transformer=False):
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
            model_, env_, model_save_path = self._get_small_cap_model(data, scenario = scenario, training_config = training_config, get_tab_transformer=get_tab_transformer)
        elif market_cap == 'medium':
            model_, env_, model_save_path = self._get_medium_cap_model(data, scenario = scenario, training_config = training_config, get_tab_transformer=get_tab_transformer)
        else:
            model_, env_, model_save_path = self._get_large_cap_model(data, scenario = scenario, training_config = training_config, get_tab_transformer=get_tab_transformer)
        if not os.path.exists(model_save_path):
            raise ValueError(f"Model not found at {model_save_path}")
        
        model_.policy.load_state_dict(torch.load(model_save_path))

        return model_
        
    def _get_large_cap_model(self, data, scenario, get_tab_transformer=False, training_config=PPO_MODEL_BEST_PARAMS):
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
            file_path = f'{self.model_dir}/model_large_cap_large.h5'
            model, env = self._get_large(data, file_path, market_cap='large', get_tab_transformer=get_tab_transformer,
                                         training_config=training_config)
        elif scenario == 'medium-large':
            print('large cap, medium-large scenario model selected')
            file_path = f'{self.model_dir}/model_large_cap_medium_large.h5'
            model, env = self._get_medium_large(data, file_path, market_cap='large',
                                                get_tab_transformer=get_tab_transformer,
                                                training_config=training_config)
        elif scenario == 'medium':
            print('large cap, medium scenario model selected')
            file_path = f'{self.model_dir}/model_large_cap_medium.h5'
            model, env = self._get_medium(data, file_path, market_cap='large', get_tab_transformer=get_tab_transformer,
                                          training_config=training_config)
        elif scenario == 'small-medium':
            print('large cap, small-medium scenario model selected')
            file_path = f'{self.model_dir}/model_large_cap_small_medium.h5'
            model, env = self._get_small_medium(data, file_path, market_cap='large',
                                                get_tab_transformer=get_tab_transformer,
                                                training_config=training_config)
        elif scenario == 'small':
            print('large cap, small scenario model selected')
            file_path = f'{self.model_dir}/model_large_cap_small.h5'
            model, env = self._get_small(data, file_path, market_cap='large', get_tab_transformer=get_tab_transformer,
                                         training_config=training_config)
        else:
            print('large cap, large scenario model selected')
            file_path = f'{self.model_dir}/model_large_cap_large.h5'
            model, env = self._get_large(data, file_path, market_cap='large', get_tab_transformer=get_tab_transformer,
                                         training_config=training_config)
        return model, env, file_path

    def _get_medium_cap_model(self, data, scenario, get_tab_transformer=False, training_config=PPO_MODEL_BEST_PARAMS):
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
            file_path = f'{self.model_dir}/model_medium_cap_large.h5'
            model, env = self._get_large(data, file_path, market_cap='medium', get_tab_transformer=get_tab_transformer,
                                         training_config=training_config)
        elif scenario == 'medium-large':
            print('Medium cap, medium-large scenario model selected')
            file_path = f'{self.model_dir}/model_medium_cap_medium_large.h5'
            model, env = self._get_medium_large(data, file_path, market_cap='medium',
                                                get_tab_transformer=get_tab_transformer,
                                                training_config=training_config)
        elif scenario == 'medium':
            print('Medium cap, medium scenario model selected')
            file_path = f'{self.model_dir}/model_medium_cap_medium.h5'
            model, env = self._get_medium(data, file_path, market_cap='medium', get_tab_transformer=get_tab_transformer,
                                          training_config=training_config)
        elif scenario == 'small-medium':
            print('Medium cap, small-medium scenario model selected')
            file_path = f'{self.model_dir}/model_medium_cap_small_medium.h5'
            model, env = self._get_small_medium(data, file_path, market_cap='medium',
                                                get_tab_transformer=get_tab_transformer,
                                                training_config=training_config)
        elif scenario == 'small':
            print('Medium cap, small scenario model selected')
            file_path = f'{self.model_dir}/model_medium_cap_small.h5'
            model, env = self._get_small(data, file_path, market_cap='medium', get_tab_transformer=get_tab_transformer,
                                         training_config=training_config)
        else:
            print('Medium cap, large scenario model selected')
            file_path = f'{self.model_dir}/model_medium_cap_large.h5'
            model, env = self._get_large(data, file_path, market_cap='medium', get_tab_transformer=get_tab_transformer,
                                         training_config=training_config)
        return model, env, file_path

    def _get_small_cap_model(self, data, scenario, get_tab_transformer=False, training_config=PPO_MODEL_BEST_PARAMS):
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
            file_path = f'{self.model_dir}/model_small_cap_large.h5'
            model, env = self._get_large(data, file_path, market_cap='small', get_tab_transformer=get_tab_transformer,
                                         training_config=training_config)
        elif scenario == 'medium-large':
            print('Small cap, medium-large scenario model selected')
            file_path = f'{self.model_dir}/model_small_cap_medium_large.h5'
            model, env = self._get_medium_large(data, file_path, market_cap='small',
                                                get_tab_transformer=get_tab_transformer,
                                                training_config=training_config)
        elif scenario == 'medium':
            print('Small cap, medium scenario model selected')
            file_path = f'{self.model_dir}/model_small_cap_medium.h5'
            model, env = self._get_medium(data, file_path, market_cap='small', get_tab_transformer=get_tab_transformer,
                                          training_config=training_config)
        elif scenario == 'small-medium':
            print('Small cap, small-medium scenario model selected')
            file_path = f'{self.model_dir}/model_small_cap_small_medium.h5'
            model, env = self._get_small_medium(data, file_path, market_cap='small',
                                                get_tab_transformer=get_tab_transformer,
                                                training_config=training_config)
        elif scenario == 'small':
            print('Small cap, small scenario model selected')
            file_path = f'{self.model_dir}/model_small_cap_small.h5'
            model, env = self._get_small(data, file_path, market_cap='small', get_tab_transformer=get_tab_transformer,
                                         training_config=training_config)
        else:
            print('Small cap, large scenario model selected')
            file_path = f'{self.model_dir}/model_small_cap_large.h5'
            model, env = self._get_large(data, file_path, market_cap='small', get_tab_transformer=get_tab_transformer,
                                         training_config=training_config)
        return model, env, file_path

    def _get_small(self, data, file_path, market_cap='large', get_tab_transformer = False, training_config=PPO_MODEL_BEST_PARAMS):
        """
        Configures and returns a PPO model for small trade scenarios.

        Args:
        - data (pd.DataFrame): Historical market data to be used in the trading environment - 1 row.

        Returns:
        - model (PPO): The PPO model configured for small trade scenarios.
        """
        # file_path = f'{self.model_dir}/model_small.h5'
        original_action_space = spaces.Box(low=np.array([0.33, 30]), high=np.array([1, 50]), dtype=np.float32)
        action_space = spaces.Box(low=np.array([-1, -1]), high=np.array([1, 1]), dtype=np.float32)

        def env(): 
            return TradingEnvironment(data, action_space, original_action_space, preferred_timeframe=390, initial_inventory=10, scenario='small')
        env_obj = env()
        scenario = 'small'
        preferred_timeframe = 390
        initial_inventory = 10
        if not get_tab_transformer:
            model = self._load_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap},
                                 training_config=training_config)
        else:
            model = self._load_tabtransformer_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap, 'state_cols': env_obj.state_columns},
                                 training_config=training_config)
        return model, env_obj

    def _get_small_medium(self, data, file_path, market_cap='large', get_tab_transformer = False, training_config=PPO_MODEL_BEST_PARAMS):
        """
        Configures and returns a PPO model for small to medium trade scenarios.

        Args:
        - data (pd.DataFrame): Historical market data to be used in the trading environmen - 1 row.

        Returns:
        - model (PPO): The PPO model configured for small to medium trade scenarios.
        """
        # file_path = 'Models/model_small_med.h5'
        preferred_timeframe = 390
        initial_inventory = 100
        original_action_space = spaces.Box(low=np.array([0.2, 20]), high=np.array([0.66, 30]), dtype=np.float32)
        action_space = spaces.Box(low=np.array([-1, -1]), high=np.array([1, 1]), dtype=np.float32)

        def env(): 
            return TradingEnvironment(data, action_space, original_action_space, preferred_timeframe=preferred_timeframe,
                                 initial_inventory=initial_inventory, scenario='small-medium')
        
        env_obj = env()
        scenario = 'small-medium'
        if not get_tab_transformer:
            model = self._load_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap},
                                 training_config=training_config)
        else:
            model = self._load_tabtransformer_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap, 'state_cols': env_obj.state_columns},
                                 training_config=training_config)
        return model, env_obj

    def _get_medium(self, data, file_path, market_cap='large', get_tab_transformer = False, training_config=PPO_MODEL_BEST_PARAMS):
        """
        Configures and returns a PPO model for medium trade scenarios.

        Args:
        - data (pd.DataFrame): Historical market data to be used in the trading environment - 1 row.

        Returns:
        - model (PPO): The PPO model configured for medium trade scenarios.
        """
        # file_path = 'Models/model_med.h5'
        preferred_timeframe = 390
        initial_inventory = 500
        original_action_space = spaces.Box(low=np.array([0.20, 30]), high=np.array([0.50, 50]), dtype=np.float32)
        action_space = spaces.Box(low=np.array([-1, -1]), high=np.array([1, 1]), dtype=np.float32)

        def env(): 
            return TradingEnvironment(data, action_space, original_action_space, preferred_timeframe=preferred_timeframe,
                                 initial_inventory=initial_inventory, scenario='medium')
        env_obj = env()
        scenario = 'medium'
        if not get_tab_transformer:
            model = self._load_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap},
                                 training_config=training_config)
        else:
            model = self._load_tabtransformer_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap, 'state_cols': env_obj.state_columns},
                                 training_config=training_config)
        return model, env_obj

    def _get_medium_large(self, data, file_path, market_cap='large', get_tab_transformer = False, training_config=PPO_MODEL_BEST_PARAMS):
        """
        Configures and returns a PPO model for medium to large trade scenarios.

        Args:
        - data (pd.DataFrame): Historical market data to be used in the trading environment - 1 row.

        Returns:
        - model (PPO): The PPO model configured for medium to large trade scenarios.
        """
        # file_path = 'Models/model_med_lg.h5'
        preferred_timeframe = 390
        initial_inventory = 2000
        original_action_space = spaces.Box(low=np.array([0.10, 30]), high=np.array([0.40, 50]), dtype=np.float32)
        action_space = spaces.Box(low=np.array([-1, -1]), high=np.array([1, 1]), dtype=np.float32)

        def env(): 
            return TradingEnvironment(data, action_space, original_action_space, preferred_timeframe=preferred_timeframe,
                                 initial_inventory=initial_inventory, scenario='medium-large')
        env_obj = env()
        scenario = 'medium-large'
        
        if not get_tab_transformer:
            model = self._load_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap},
                                 training_config=training_config)
        else:
            model = self._load_tabtransformer_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap, 'state_cols': env_obj.state_columns},
                                 training_config=training_config)
        return model, env_obj

    def _get_large(self, data, file_path, market_cap='large', get_tab_transformer = False, training_config=PPO_MODEL_BEST_PARAMS):
        """
        Configures and returns a PPO model for large trade scenarios.

        Args:
        - data (pd.DataFrame): Historical market data to be used in the trading environment - 1 row.

        Returns:
        - model (PPO): The PPO model configured for large trade scenarios.
        """
        # file_path = 'Models/model_lg_cap_.h5'
        preferred_timeframe = 390
        initial_inventory = 10000
        original_action_space = spaces.Box(low=np.array([0.05, 30]), high=np.array([0.33, 50]), dtype=np.float32)
        action_space = spaces.Box(low=np.array([-1, -1]), high=np.array([1, 1]), dtype=np.float32)

        def env(): 
            return TradingEnvironment(data, action_space, original_action_space, preferred_timeframe=preferred_timeframe,
                                 initial_inventory=initial_inventory, scenario='large')
        env_obj = env()
        scenario = 'large'
        if not get_tab_transformer:
            model = self._load_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap},
                                 training_config=training_config)
        else:
            model = self._load_tabtransformer_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap, 'state_cols': env_obj.state_columns},
                                 training_config=training_config)
        return model, env_obj

    def train(self, data, scenario='medium', market_cap="large", get_tab_transformer = False, training_config=PPO_MODEL_BEST_PARAMS, resume=False,
              training_params={}):
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

        # Get the model
        if market_cap == "large":
            model_, env_, model_save_path = self._get_large_cap_model(data, scenario, get_tab_transformer = get_tab_transformer, training_config=training_config)
        elif market_cap == "medium":
            model_, env_, model_save_path = self._get_medium_cap_model(data, scenario, get_tab_transformer = get_tab_transformer, training_config=training_config)
        elif market_cap == "small":
            model_, env_, model_save_path = self._get_small_cap_model(data, scenario, get_tab_transformer = get_tab_transformer, training_config=training_config)
        else:
            model_, env_, model_save_path = self._get_large_cap_model(data, scenario, get_tab_transformer = get_tab_transformer, training_config=training_config)

        if resume:
            if os.path.exists(model_save_path):
                # Load the model
                filepath = model_save_path
                model_.policy.load_state_dict(torch.load(filepath))
                print(f"Model loaded from {filepath}")
            else:
                print(f"Model not found at {model_save_path}, training from scratch...")

        # Train the model

        model_.learn(**training_params)
        # Save the model
        self.save_model(model_, model_save_path)

        if self.multi_env:
            self.multi_env.close()
            gc.collect()
                  
        return model_, env_

    def test(self, data, model=None, get_tab_transformer = False, market_cap="large", scenario="medium", seed=None):
        # if model is None:
        if market_cap == "large":
            model_, env_, model_save_path = self._get_large_cap_model(data, scenario, get_tab_transformer = get_tab_transformer)
        elif market_cap == "medium":
            model_, env_, model_save_path = self._get_medium_cap_model(data, scenario, get_tab_transformer = get_tab_transformer)
        elif market_cap == "small":
            model_, env_, model_save_path = self._get_small_cap_model(data, scenario, get_tab_transformer = get_tab_transformer)
        else:
            model_, env_, model_save_path = self._get_large_cap_model(data,  scenario, get_tab_transformer = get_tab_transformer)
        
        if model is None:
            if os.path.exists(model_save_path):
                print(f"Loading model from {model_save_path}")
                model_.policy.load_state_dict(torch.load(model_save_path))
            else:
                print(f"Model not found at {model_save_path}, Random model will be used")
            model = model_
        
        with torch.no_grad():
            obs = env_.reset(randomize=False)
            cum_reward = 0
            actions = []
            for _ in range(len(data)):
                action, _states = model.predict(obs,deterministic=True)
                actions.append(action)
                obs, rewards, done, info = env_.step(action)
                cum_reward += rewards
                if done:
                    break
        trades = pd.DataFrame(env_.trades)
        trades['raw_actions'] = actions
        return cum_reward, env_, trades

    def save_model(self,model, filepath):
        # Save the model parameters
        torch.save(model.policy.state_dict(), filepath)
        # print(f"Model saved to {filepath}")

    def fine_tuning_model(self, config):
        train_data = config['train_data']
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
        model =self.train(train_data, market_cap, scenario, training_config, resume, training_params)

        rew = self.test(test_data, model)

        tune.report({"reward":rew})

        return 

    def infer_macro(self, timeframe, transaction_size, market_cap_int, input_data, data, meta = MetaLearner(), inference_data_handler = InferenceDataHandler(),get_tab_transformer = False):
        """
        Infers macro trading decisions based on the given timeframe, transaction size, market capitalization, input data, and additional data.

        Parameters:
            timeframe (int): The preferred timeframe for trading.
            transaction_size (int): The initial inventory for trading.
            market_cap_int (int): The market capitalization of the asset.
            input_data (object): The input data for the model.
            data (object): Additional data for real-time forecasting.

        Returns:
            tuple: A tuple containing the trades and micro input data.
        """
        scenario = meta.classify_scenario(transaction_size, timeframe)
        market_cap = meta.classify_market_cap(market_cap_int)
        # print(f"Scenario: {scenario}")

        model = self.get_model(input_data,market_cap=market_cap,scenario=scenario,get_tab_transformer = get_tab_transformer)
        with torch.no_grad():
            original_action_space = spaces.Box(low=np.array([0.10, 30]), high=np.array([0.40, 50]), dtype=np.float32)
            action_space = spaces.Box(low=np.array([-1, -1]), high=np.array([1, 1]), dtype=np.float32)

            env = TradingEnvironment(input_data, scenario=scenario,original_action_space=original_action_space, preferred_timeframe=timeframe, initial_inventory=transaction_size,inference=True)
            obs = env.reset()
            obs = obs.astype(np.float32)
            done = False
            forecast_step = 0
            observations = []
            state_cols = env.state_columns
            while not done:
                action, _states = model.predict(obs)
                step = int(np.ceil(action[1]))
                forecast_step += step
                obs = inference_data_handler.add_real_time_forecasts(data, forecast_step)
                # print(obs.columns)
                obs = obs.squeeze()
                observations.append(obs)
                obs = obs[state_cols]
                done, info = env.step(action)

                if done:
                    break

        micro_input = pd.DataFrame(observations)
        # trades = env.render()

        trades = pd.DataFrame(env.trades)
        micro_input["shares"] = trades['shares'].values
        return trades, micro_input
