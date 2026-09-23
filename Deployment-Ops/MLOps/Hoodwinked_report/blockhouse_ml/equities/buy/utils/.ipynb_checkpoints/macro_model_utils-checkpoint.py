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
import pytz
from blockhouse_ml.equities.buy.utils.macro_model import PPO_MODEL_BEST_PARAMS, MetaLearner
from blockhouse_ml.equities.buy.utils.macro_model import CustomTransformerPolicy, MetaLearner, PPO_MODEL_BEST_PARAMS, PPO_MODEL_BEST_PARAMS_TAB, TabTransformerPolicy
from blockhouse_ml.equities.buy.utils.env import CustomTradingEnvironment, TradingEnvironmentMacroV2
from blockhouse_ml.equities.buy.utils.data_handler import InferenceDataHandler


class MacroTraderModel:
    """
    This class is responsible for training, saving, and loading models for different trading scenarios. 
    Each method in the class loads a model configured with specific hyperparameters and action spaces 
    based on the trading scenario (small, small-medium, medium, medium-large, large).
    """

    def __init__(self, model_dir = 'BuyEquityModels'):
        """
        Initializes the Model class.
        """
        self.model_dir = model_dir
        os.makedirs(model_dir, exist_ok=True)
    

        
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
        model = PPO(CustomTransformerPolicy, env, policy_kwargs=policy_kwargs, **training_config)
        # model.policy.load_state_dict(torch.load(filepath))
        # print(f"Model loaded from {filepath}")
        
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
        training_config=PPO_MODEL_BEST_PARAMS_TAB
        policy_kwargs['state_cols'] = env.state_columns
        model = PPO(TabTransformerPolicy, env, policy_kwargs=policy_kwargs, **training_config)

        return model

    
    def get_model(self, data, market_cap, scenario, training_config = PPO_MODEL_BEST_PARAMS):
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
            model_, env_, model_save_path = self._get_small_cap_model(data, scenario = scenario, training_config = training_config)
        elif market_cap == 'medium':
            model_, env_, model_save_path = self._get_medium_cap_model(data, scenario = scenario, training_config = training_config)
        else:
            print(scenario)
            model_, env_, model_save_path = self._get_large_cap_model(data, scenario = scenario, training_config = training_config)
        print("model_save_path",model_save_path)
        print("loading latest model")
        if not os.path.exists(model_save_path):
            raise ValueError(f"Model not found at {model_save_path}")
        
        model_.policy.load_state_dict(torch.load(model_save_path))

        return model_
        
    def _get_large_cap_model(self, data, scenario, get_tab_transformer=True, training_config=PPO_MODEL_BEST_PARAMS):
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
        env = TradingEnvironmentMacroV2(data, action_space, original_action_space, preferred_timeframe=preferred_timeframe,
                                 target_shares=target_shares, scenario='small')
        scenario = 'small'
        preferred_timeframe = 200
        target_shares = 10
        if not get_tab_transformer:
            model = self._load_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap},
                                 training_config=training_config)
        else:
            model = self._load_tabtransformer_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap},
                                 training_config=training_config)
        return model, env

    def _get_small_medium(self, data, file_path, market_cap='large', get_tab_transformer = False, training_config=PPO_MODEL_BEST_PARAMS):
        """
        Configures and returns a PPO model for small to medium trade scenarios.

        Args:
        - data (pd.DataFrame): Historical market data to be used in the trading environmen - 1 row.

        Returns:
        - model (PPO): The PPO model configured for small to medium trade scenarios.
        """
        # file_path = 'Models/model_small_med.h5'
        preferred_timeframe = 200
        target_shares = 100
        original_action_space = spaces.Box(low=np.array([0.2, 20]), high=np.array([0.66, 30]), dtype=np.float32)
        action_space = spaces.Box(low=np.array([-1, -1]), high=np.array([1, 1]), dtype=np.float32)
        env = TradingEnvironmentMacroV2(data, action_space, original_action_space, preferred_timeframe=preferred_timeframe,
                                 target_shares=target_shares, scenario='small-medium')
        scenario = 'small-medium'
        if not get_tab_transformer:
            model = self._load_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap},
                                 training_config=training_config)
        else:
            model = self._load_tabtransformer_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap},
                                 training_config=training_config)
        return model, env

    def _get_medium(self, data, file_path, market_cap='large', get_tab_transformer = False, training_config=PPO_MODEL_BEST_PARAMS):
        """
        Configures and returns a PPO model for medium trade scenarios.

        Args:
        - data (pd.DataFrame): Historical market data to be used in the trading environment - 1 row.

        Returns:
        - model (PPO): The PPO model configured for medium trade scenarios.
        """
        # file_path = 'Models/model_med.h5'
        preferred_timeframe = 200
        target_shares = 500
        original_action_space = spaces.Box(low=np.array([0.20, 30]), high=np.array([0.50, 50]), dtype=np.float32)
        action_space = spaces.Box(low=np.array([-1, -1]), high=np.array([1, 1]), dtype=np.float32)
        env=TradingEnvironmentMacroV2(data,action_space,original_action_space,preferred_timeframe=preferred_timeframe,target_shares=target_shares,scenario='medium')
        scenario = 'medium'
        if not get_tab_transformer:
            model = self._load_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap},
                                 training_config=training_config)
        else:
            model = self._load_tabtransformer_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap},
                                 training_config=training_config)
        return model, env

    def _get_medium_large(self, data, file_path, market_cap='large', get_tab_transformer = False, training_config=PPO_MODEL_BEST_PARAMS):
        """
        Configures and returns a PPO model for medium to large trade scenarios.

        Args:
        - data (pd.DataFrame): Historical market data to be used in the trading environment - 1 row.

        Returns:
        - model (PPO): The PPO model configured for medium to large trade scenarios.
        """
        # file_path = 'Models/model_med_lg.h5'
        preferred_timeframe = 200
        target_shares = 2000
        original_action_space = spaces.Box(low=np.array([0.10, 30]), high=np.array([0.40, 50]), dtype=np.float32)
        action_space = spaces.Box(low=np.array([-1, -1]), high=np.array([1, 1]), dtype=np.float32)
        env = TradingEnvironmentMacroV2(data, action_space, original_action_space, preferred_timeframe=preferred_timeframe,
                                 target_shares=target_shares, scenario='medium-large')
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

    def _get_large(self, data, file_path, market_cap='large', get_tab_transformer = False, training_config=PPO_MODEL_BEST_PARAMS):
        """
        Configures and returns a PPO model for large trade scenarios.

        Args:
        - data (pd.DataFrame): Historical market data to be used in the trading environment - 1 row.

        Returns:
        - model (PPO): The PPO model configured for large trade scenarios.
        """
        # file_path = 'Models/model_lg_cap_.h5'
        preferred_timeframe = 200
        target_shares = 10000
        original_action_space = spaces.Box(low=np.array([0.05, 30]), high=np.array([0.33, 50]), dtype=np.float32)
        action_space = spaces.Box(low=np.array([-1, -1]), high=np.array([1, 1]), dtype=np.float32)
        env = TradingEnvironmentMacroV2(data, action_space, original_action_space, preferred_timeframe=preferred_timeframe,
                                 target_shares=target_shares, scenario='large')
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

    
    
    def train(self, data, scenario='medium', market_cap="large", get_tab_transformer=False, training_config=PPO_MODEL_BEST_PARAMS, resume=False,
              training_params={}):
        # Get the model
        if market_cap == "large":
            model_, env_, model_save_path = self._get_large_cap_model(data, scenario, get_tab_transformer=get_tab_transformer, training_config=training_config)
        elif market_cap == "medium":
            model_, env_, model_save_path = self._get_medium_cap_model(data, scenario, get_tab_transformer=get_tab_transformer, training_config=training_config)
        elif market_cap == "small":
            model_, env_, model_save_path = self._get_small_cap_model(data, scenario, get_tab_transformer=get_tab_transformer, training_config=training_config)
        else:
            model_, env_, model_save_path = self._get_large_cap_model(data, scenario, get_tab_transformer=get_tab_transformer, training_config=training_config)

        if resume:
            if os.path.exists(model_save_path):
                # Load the model
                filepath = model_save_path
                model_.policy.load_state_dict(torch.load(filepath))
                print(f"Model loaded from {filepath}")
            else:
                print(f"Model not found at {model_save_path}, training from scratch...")

        # Train the model
        model_.learn(total_timesteps=training_params['total_timesteps'], callback=training_params.get('callback'))

        # Save the model
        self.save_model(model_, model_save_path)

        return model_, env_

    
    
    
#     def train(self, data, scenario='medium', market_cap="large", get_tab_transformer = False, training_config=PPO_MODEL_BEST_PARAMS, resume=False,
#               training_params={}):
#         """
#         Trains a MacroTrader model based on the provided data, scenario, market capitalization, and training configuration.

#         Args: data: The input data used for training the model. scenario (str): The scenario of the model to train. 
#         Defaults to 'medium'. market_cap (str): The market capitalization of the model to train. Can be 'small', 
#         'medium', or 'large'. Defaults to 'large'. total_timesteps (int): The total number of timesteps to train the 
#         model for. Defaults to 10000. training_config (dict): The training configuration for the model. Defaults to 
#         PPO_MODEL_BEST_PARAMS, can be used for tuning hyperparameters. resume (bool): Whether to resume training from 
#         a saved model. Defaults to False. training_params (dict): Additional training parameters used in model.learn 
#         method. Defaults to {}.

#         Returns:
#             None
#         """

#         # Get the model
#         if market_cap == "large":
#             model_, env_, model_save_path = self._get_large_cap_model(data, scenario, get_tab_transformer = get_tab_transformer, training_config=training_config)
#         elif market_cap == "medium":
#             model_, env_, model_save_path = self._get_medium_cap_model(data, scenario, get_tab_transformer = get_tab_transformer, training_config=training_config)
#         elif market_cap == "small":
#             model_, env_, model_save_path = self._get_small_cap_model(data, scenario, get_tab_transformer = get_tab_transformer, training_config=training_config)
#         else:
#             model_, env_, model_save_path = self._get_large_cap_model(data, scenario, get_tab_transformer = get_tab_transformer, training_config=training_config)

#         if resume:
#             if os.path.exists(model_save_path):
#                 # Load the model
#                 filepath = model_save_path
#                 model_.policy.load_state_dict(torch.load(filepath))
#                 print(f"Model loaded from {filepath}")
#             else:
#                 print(f"Model not found at {model_save_path}, training from scratch...")

#         # Train the model

#         model_.learn(**training_params)
#         # Save the model
#         self.save_model(model_, model_save_path)
                  
#         return model_, env_

    def test(self, data, model=None, get_tab_transformer = False, market_cap="large", scenario="medium"):
        # if model is None:
        if market_cap == "large":
            model_, env_, model_save_path = self._get_large_cap_model(data, scenario, get_tab_transformer = get_tab_transformer)
        elif market_cap == "medium":
            model_, env_, model_save_path = self._get_medium_cap_model(data, scenario, get_tab_transformer = get_tab_transformer)
        elif market_cap == "small":
            model_, env_, model_save_path = self._get_small_cap_model(data, scenario, get_tab_transformer = get_tab_transformer)
        else:
            model_, env_, model_save_path = self._get_large_cap_model(data,  scenario, get_tab_transformer = get_tab_transformer)
        # if not os.path.exists(model_save_path):
        #     raise ValueError(f"Model not found at {model_save_path}")
        
        if model is None:
            if os.path.exists(model_save_path):
                print(f"Loading model from {model_save_path}")
                model_.policy.load_state_dict(torch.load(model_save_path))
            else:
                print(f"Model not found at {model_save_path}, Random model will be used")
            model = model_
        
        
        with torch.no_grad():
            obs = env_.reset()
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
        
        
        
        
#         with torch.no_grad():
#             obs = env_.reset()
#             cum_reward = 0
#             for _ in range(len(data)):
#                 action, _states = model.predict(obs, deterministic=True)

#                 obs, rewards, done, info = env_.step(action)
#                 cum_reward += rewards
#                 if done:
#                     break
#         return cum_reward, env_

    def save_model(self,model, filepath):
        # Save the model parameters
        torch.save(model.policy.state_dict(), filepath)
        # print(f"Model saved to {filepath}")

    def fine_tuning_model(self, config):
        train_data = config['train_data']
        market_cap = config['market_cap']
        scenario = config['scenario']
        training_config = {
            'learning_rate': config['learning_rate'],
            'n_steps': config['n_steps'],
            'batch_size': config['batch_size'],
            'gamma': config['gamma'],
            'clip_range': config['clip_range'],
            'n_epochs': config['n_epochs'],
            'ent_coef': config['ent_coef']
        }
        resume = config['resume']

        # Ensure 'total_timesteps' is provided, with a default value of 10000
        training_params = {
            "total_timesteps": config.get('total_timesteps', 10000),
            "callback": config.get('callback', None)
        }

        test_data = config['test_data']
        model = self.train(train_data, scenario=scenario, market_cap=market_cap, training_config=training_config, resume=resume, training_params=training_params)

        rew = self.test(test_data, model)

        tune.report({"reward": rew})

        return 

        
        
        
#     def fine_tuning_model(self, config):
#         train_data = config['train_data']
#         market_cap = config['market_cap']
#         scenario = config['scenario']
#         training_config = {}
#         training_config['learning_rate'] = config['learning_rate']
#         training_config['n_steps'] = config['n_steps']
#         training_config['batch_size'] = config['batch_size']
#         training_config['gamma'] = config['gamma']
#         training_config['clip_range'] = config['clip_range']
#         training_config['n_epochs'] = config['n_epochs']
#         training_config['ent_coef'] = config['ent_coef']
#         resume = config['resume']

#         training_params = {}
#         training_params["total_timesteps"] = config['total_timesteps']
#         training_params["callback"] = config['callback']

#         test_data = config['test_data']
#         model =self.train(train_data, market_cap, scenario, training_config, resume, training_params)

#         rew = self.test(test_data, model)

#         tune.report({"reward":rew})

#         return 
    
    
    
    
    def _unscale_action(scaled_action, low, high):
        """
        Rescale the action from [-1, 1] to [low, high]
        (no need for symmetric action space)

        :param scaled_action: Action to un-scale
        """
        return low + (0.5 * (scaled_action + 1.02) * (high - low))

    def infer_macro(self, timeframe, transaction_size, market_cap_int, input_data, data, meta = MetaLearner(), inference_data_handler = InferenceDataHandler()):
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

        model = self.get_model(input_data,market_cap=market_cap,scenario=scenario)
        with torch.no_grad():
            # action_space = spaces.Box(low=np.array([0.10, 30]), high=np.array([0.40, 50]), dtype=np.float32)
            original_action_space = spaces.Box(low=np.array([0.05, 30]), high=np.array([0.33, 50]), dtype=np.float32)
            action_space = spaces.Box(low=np.array([-1, -1]), high=np.array([1, 1]), dtype=np.float32)

            up_time = original_action_space.high[1]
            down_time = original_action_space.low[1]

            up_amount = original_action_space.high[0]
            down_amount = original_action_space.low[0]

            adjusted_up = round(timeframe * up_time / 390)
            adjusted_down = round(timeframe* down_time / 390)
            low = np.array([down_amount, adjusted_down])
            high = np.array([up_amount, adjusted_up])
            
            env = CustomTradingEnvironment(input_data, scenario, action_space,original_action_space, preferred_timeframe=timeframe, target_shares=transaction_size)
            obs = env.reset()
            obs = obs.astype(np.float32)
            done = False
            forecast_step = 0
            observations = []
            state_cols = ['open','high','low','close', 'volume', 'RSI', 'MACD', 'MACD_signal', 'MACD_hist', 
                                        'Stoch_k', 'Stoch_d', 'OBV', 'Upper_BB', 'Middle_BB', 'Lower_BB', 'ATR_1', 'ADX', 
                                        '+DI', '-DI', 'CCI', 'transaction_cost', 'forecast_6Hr_open','forecast_6Hr_close',
                                        'forecast_6Hr_high','forecast_6Hr_low', 'forecast_6Hr_volatility', 
                                        'forecast_6Hr_volume', 'forecast_6Hr_transaction_cost']

            while not done:
                action, _states = model.predict(obs)
                action_1 = float(action[1].item() if hasattr(action[1], 'item') else action[1])
                action_step = env._unscale_action(action)
                step = int(np.ceil(action_step[1]))
                # print(f"step {step}")
                forecast_step += step
                # print(f"forecaststep {forecast_step}")
                obs = inference_data_handler.add_real_time_forecasts(data, forecast_step, model_type="micro")
                obs = obs.squeeze()
                observations.append(obs)
                obs = obs[state_cols]
                done, info = env.step(action)

                if done:
                    break

        micro_input = pd.DataFrame(observations)
        # print(micro_input.columns)
        # trades = pd.DataFrame(trades)
        # print("####################################")
        # print(trades.columns)
        trades = env.render()
        tradess = env.print_trades()
        
        tradess = pd.DataFrame(tradess)
        # print(tradess.columns)
        # micro_input["shares"] = trades['shares'].values
        return tradess, micro_input
        
        
                       # action =  low + (0.5 * (action + 1.02) * (high - low))
                # action = _unscale_action(action, low ,high)