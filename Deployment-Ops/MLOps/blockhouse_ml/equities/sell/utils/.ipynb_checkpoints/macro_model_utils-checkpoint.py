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

from blockhouse_ml.equities.sell.utils.macro_model import PPO_MODEL_BEST_PARAMS, MetaLearner
from blockhouse_ml.equities.sell.utils.macro_model import CustomTransformerPolicy, MetaLearner, PPO_MODEL_BEST_PARAMS, PPO_MODEL_BEST_PARAMS_TAB, TabTransformerPolicy
from blockhouse_ml.equities.sell.utils.env import TradingEnvironment, CustomTradingEnvironment
from blockhouse_ml.equities.sell.utils.data_handler import InferenceDataHandler


class MacroTraderModel:
    """
    This class is responsible for training, saving, and loading models for different trading scenarios. 
    Each method in the class loads a model configured with specific hyperparameters and action spaces 
    based on the trading scenario (small, small-medium, medium, medium-large, large).
    """

    def __init__(self, model_dir = 'Models'):
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

    
    def get_model(self, data, market_cap, scenario, training_config = PPO_MODEL_BEST_PARAMS, transaction_size =10000):
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
            model_, env_, model_save_path = self._get_small_cap_model(data, scenario = scenario, training_config = training_config, transaction_size = transaction_size)
        elif market_cap == 'medium':
            model_, env_, model_save_path = self._get_medium_cap_model(data, scenario = scenario, training_config = training_config, transaction_size = transaction_size)
        else:
            model_, env_, model_save_path = self._get_large_cap_model(data, scenario = scenario, training_config = training_config, transaction_size =transaction_size)
            print("model path for macro ", model_save_path)
        if not os.path.exists(model_save_path):
            raise ValueError(f"Model not found at {model_save_path}")
        
        model_.policy.load_state_dict(torch.load(model_save_path))

        return model_
        
    def _get_large_cap_model(self, data, scenario, get_tab_transformer=False, training_config=PPO_MODEL_BEST_PARAMS,  transaction_size = 10000):
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
                                         training_config=training_config, transaction_size = transaction_size)
        elif scenario == 'medium-large':
            print('large cap, medium-large scenario model selected')
            file_path = f'{self.model_dir}/model_large_cap_medium_large.h5'
            model, env = self._get_medium_large(data, file_path, market_cap='large',
                                                get_tab_transformer=get_tab_transformer,
                                                training_config=training_config, transaction_size = transaction_size)
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
                                                training_config=training_config, transaction_size = transaction_size)
        elif scenario == 'small':
            print('large cap, small scenario model selected')
            file_path = f'{self.model_dir}/model_large_cap_small.h5'
            model, env = self._get_small(data, file_path, market_cap='large', get_tab_transformer=get_tab_transformer,
                                         training_config=training_config)
        else:
            print('large cap, large scenario model selected')
            file_path = f'{self.model_dir}/model_large_cap_large.h5'
            model, env = self._get_large(data, file_path, market_cap='large', get_tab_transformer=get_tab_transformer,
                                         training_config=training_config,  transaction_size = transaction_size)
        return model, env, file_path

    def _get_medium_cap_model(self, data, scenario, get_tab_transformer=False, training_config=PPO_MODEL_BEST_PARAMS, transaction_size =10000):
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
                                         training_config=training_config,  transaction_size = transaction_size)
        elif scenario == 'medium-large':
            print('Medium cap, medium-large scenario model selected')
            file_path = f'{self.model_dir}/model_medium_cap_medium_large.h5'
            model, env = self._get_medium_large(data, file_path, market_cap='medium',
                                                get_tab_transformer=get_tab_transformer,
                                                training_config=training_config,  transaction_size = transaction_size)
        elif scenario == 'medium':
            print('Medium cap, medium scenario model selected')
            file_path = f'{self.model_dir}/model_medium_cap_medium.h5'
            model, env = self._get_medium(data, file_path, market_cap='medium', get_tab_transformer=get_tab_transformer,
                                          training_config=training_config,  transaction_size = transaction_size)
        elif scenario == 'small-medium':
            print('Medium cap, small-medium scenario model selected')
            file_path = f'{self.model_dir}/model_medium_cap_small_medium.h5'
            model, env = self._get_small_medium(data, file_path, market_cap='medium',
                                                get_tab_transformer=get_tab_transformer,
                                                training_config=training_config,  transaction_size = transaction_size)
        elif scenario == 'small':
            print('Medium cap, small scenario model selected')
            file_path = f'{self.model_dir}/model_medium_cap_small.h5'
            model, env = self._get_small(data, file_path, market_cap='medium', get_tab_transformer=get_tab_transformer,
                                         training_config=training_config,  transaction_size = transaction_size)
        else:
            print('Medium cap, large scenario model selected')
            file_path = f'{self.model_dir}/model_medium_cap_large.h5'
            model, env = self._get_large(data, file_path, market_cap='medium', get_tab_transformer=get_tab_transformer,
                                         training_config=training_config,  transaction_size = transaction_size)
        return model, env, file_path

    def _get_small_cap_model(self, data, scenario, get_tab_transformer=False, training_config=PPO_MODEL_BEST_PARAMS,  transaction_size =10000 ):
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
                                         training_config=training_config,  transaction_size = transaction_size)
        elif scenario == 'medium-large':
            print('Small cap, medium-large scenario model selected')
            file_path = f'{self.model_dir}/model_small_cap_medium_large.h5'
            model, env = self._get_medium_large(data, file_path, market_cap='small',
                                                get_tab_transformer=get_tab_transformer,
                                                training_config=training_config, transaction_size = transaction_size)
        elif scenario == 'medium':
            print('Small cap, medium scenario model selected')
            file_path = f'{self.model_dir}/model_small_cap_medium.h5'
            model, env = self._get_medium(data, file_path, market_cap='small', get_tab_transformer=get_tab_transformer,
                                          training_config=training_config, transaction_size = transaction_size)
        elif scenario == 'small-medium':
            print('Small cap, small-medium scenario model selected')
            file_path = f'{self.model_dir}/model_small_cap_small_medium.h5'
            model, env = self._get_small_medium(data, file_path, market_cap='small',
                                                get_tab_transformer=get_tab_transformer,
                                                training_config=training_config,  transaction_size = transaction_size)
        elif scenario == 'small':
            print('Small cap, small scenario model selected')
            file_path = f'{self.model_dir}/model_small_cap_small.h5'
            model, env = self._get_small(data, file_path, market_cap='small', get_tab_transformer=get_tab_transformer,
                                         training_config=training_config,  transaction_size = transaction_size)
        else:
            print('Small cap, large scenario model selected')
            file_path = f'{self.model_dir}/model_small_cap_large.h5'
            model, env = self._get_large(data, file_path, market_cap='small', get_tab_transformer=get_tab_transformer,
                                         training_config=training_config,  transaction_size = transaction_size)
        return model, env, file_path

    def _get_small(self, data, file_path, market_cap='large', get_tab_transformer = False, training_config=PPO_MODEL_BEST_PARAMS,  transaction_size =10000 ):
        """
        Configures and returns a PPO model for small trade scenarios.

        Args:
        - data (pd.DataFrame): Historical market data to be used in the trading environment - 1 row.

        Returns:
        - model (PPO): The PPO model configured for small trade scenarios.
        """
        # file_path = f'{self.model_dir}/model_small.h5'
        action_space = spaces.Box(low=np.array([0.33, 30]), high=np.array([1, 50]), dtype=np.float32)
        env = TradingEnvironment(data, action_space, preferred_timeframe=390, initial_inventory=10, scenario='small')
        scenario = 'small'
        preferred_timeframe = 390
        initial_inventory = 10
        if not get_tab_transformer:
            model = self._load_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap},
                                 training_config=training_config)
        else:
            model = self._load_tabtransformer_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap},
                                 training_config=training_config)
        return model, env

    def _get_small_medium(self, data, file_path, market_cap='large', get_tab_transformer = False, training_config=PPO_MODEL_BEST_PARAMS,  transaction_size =10000):
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
        action_space = spaces.Box(low=np.array([0.2, 20]), high=np.array([0.66, 30]), dtype=np.float32)
        env = TradingEnvironment(data, action_space, preferred_timeframe=preferred_timeframe,
                                 initial_inventory=initial_inventory, scenario='small-medium')
        scenario = 'small-medium'
        if not get_tab_transformer:
            model = self._load_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap},
                                 training_config=training_config)
        else:
            model = self._load_tabtransformer_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap},
                                 training_config=training_config)
        return model, env

    def _get_medium(self, data, file_path, market_cap='large', get_tab_transformer = False, training_config=PPO_MODEL_BEST_PARAMS,  transaction_size =10000 ):
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
        action_space = spaces.Box(low=np.array([0.20, 30]), high=np.array([0.50, 50]), dtype=np.float32)
        env = TradingEnvironment(data, action_space, preferred_timeframe=preferred_timeframe,
                                 initial_inventory=initial_inventory, scenario='medium')
        scenario = 'medium'
        if not get_tab_transformer:
            model = self._load_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap},
                                 training_config=training_config)
        else:
            model = self._load_tabtransformer_model(env, file_path, {'scenario': scenario, 'market_cap': market_cap},
                                 training_config=training_config)
        return model, env

    def _get_medium_large(self, data, file_path, market_cap='large', get_tab_transformer = False, training_config=PPO_MODEL_BEST_PARAMS,  transaction_size =10000):
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
        action_space = spaces.Box(low=np.array([0.17, 30]), high=np.array([0.40, 50]), dtype=np.float32)
        env = TradingEnvironment(data, action_space, preferred_timeframe=preferred_timeframe,
                                 initial_inventory=initial_inventory, scenario='medium-large')
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

    def _get_large(self, data, file_path, market_cap='large', get_tab_transformer = False, training_config=PPO_MODEL_BEST_PARAMS,  transaction_size =10000):
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
        scenario = 'large'
        action_space = spaces.Box(low=np.array([0.17, 30]), high=np.array([0.33, 50]), dtype=np.float32)
        # env = CustomTradingEnvironment(data, scenario, action_space, preferred_timeframe=preferred_timeframe, initial_inventory=transaction_size)
        env = TradingEnvironment(data, action_space, preferred_timeframe=preferred_timeframe,
                                 initial_inventory=initial_inventory, scenario='large')
       
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
                  
        return model_, env_

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
        if not os.path.exists(model_save_path):
            raise ValueError(f"Model not found at {model_save_path}")
        
        if model is None:
            model_.policy.load_state_dict(torch.load(model_save_path))
            model = model_
        
        with torch.no_grad():
            obs = env_.reset()
            cum_reward = 0
            for _ in range(len(data)):
                action, _states = model.predict(obs)
                obs, rewards, done, info = env_.step(action)
                cum_reward += rewards
                if done:
                    break
        return cum_reward, env_

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

    def infer_macro(self, timeframe, transaction_size, market_cap_int, input_data, data, meta=MetaLearner(), inference_data_handler=InferenceDataHandler()):
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

        # Define action space based on the scenario
        if scenario == 'small':
            action_space = spaces.Box(low=np.array([0.17, 30]), high=np.array([0.33, 50]), dtype=np.float32)
        elif scenario == 'small-medium':
            action_space = spaces.Box(low=np.array([0.20, 20]), high=np.array([0.66, 30]), dtype=np.float32)
        elif scenario == 'medium':
            action_space = spaces.Box(low=np.array([0.20, 30]), high=np.array([0.50, 50]), dtype=np.float32)
        elif scenario == 'medium-large':
            action_space = spaces.Box(low=np.array([0.17, 30]), high=np.array([0.40, 50]), dtype=np.float32)
        else:  # scenario == 'large'
            action_space = spaces.Box(low=np.array([0.17, 30]), high=np.array([0.33, 50]), dtype=np.float32)

        model = self.get_model(input_data, market_cap=market_cap, scenario=scenario, transaction_size=transaction_size)
        with torch.no_grad():
            env = CustomTradingEnvironment(input_data, scenario, action_space, preferred_timeframe=timeframe, initial_inventory=transaction_size)
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
                action, _states = model.predict(obs, deterministic=True)
                step = int(np.ceil(action[1]))
                forecast_step += step
                obs = inference_data_handler.add_real_time_forecasts(data, forecast_step, model_type="micro")
                obs = obs.squeeze()

                # Extract 'close' price as 'expected_price'
                expected_price = obs['close']

                # Append 'expected_price' along with other observations
                obs_dict = {col: obs[col] for col in state_cols}
                obs_dict['expected_price'] = expected_price  # Add expected_price from close price
                observations.append(obs_dict)  # Store the observation as a dictionary

                obs = obs[state_cols]
                done, info = env.step(action)

                if done:
                    break

        micro_input = pd.DataFrame(observations)
        trades = env.render()

        trades = pd.DataFrame(trades)
        micro_input["shares"] = trades['shares'].values
        return trades, micro_input
    
    
    
    
#     def infer_macro(self, timeframe, transaction_size, market_cap_int, input_data, data, meta = MetaLearner(), inference_data_handler = InferenceDataHandler()):
#         """
#         Infers macro trading decisions based on the given timeframe, transaction size, market capitalization, input data, and additional data.

#         Parameters:
#             timeframe (int): The preferred timeframe for trading.
#             transaction_size (int): The initial inventory for trading.
#             market_cap_int (int): The market capitalization of the asset.
#             input_data (object): The input data for the model.
#             data (object): Additional data for real-time forecasting.

#         Returns:
#             tuple: A tuple containing the trades and micro input data.
#         """
#         scenario = meta.classify_scenario(transaction_size, timeframe)
#         market_cap = meta.classify_market_cap(market_cap_int)

#         model= self.get_model(input_data, market_cap=market_cap, scenario=scenario, transaction_size =transaction_size)
#         with torch.no_grad():
#             action_space = spaces.Box(low=np.array([0.17, 30]), high=np.array([0.40, 50]), dtype=np.float32)
#             env = CustomTradingEnvironment(input_data, scenario, action_space, preferred_timeframe=timeframe, initial_inventory=transaction_size)
#             obs = env.reset()
#             obs = obs.astype(np.float32)
#             done = False
#             forecast_step = 0
#             observations = []
#             state_cols = ['open','high','low','close', 'volume', 'RSI', 'MACD', 'MACD_signal', 'MACD_hist', 
#                                         'Stoch_k', 'Stoch_d', 'OBV', 'Upper_BB', 'Middle_BB', 'Lower_BB', 'ATR_1', 'ADX', 
#                                         '+DI', '-DI', 'CCI', 'transaction_cost', 'forecast_6Hr_open','forecast_6Hr_close',
#                                         'forecast_6Hr_high','forecast_6Hr_low', 'forecast_6Hr_volatility', 
#                                         'forecast_6Hr_volume', 'forecast_6Hr_transaction_cost']

#             while not done:
#                 action, _states = model.predict(obs, deterministic=True)
#                 step = int(np.ceil(action[1]))
#                 forecast_step += step
#                 obs = inference_data_handler.add_real_time_forecasts(data, forecast_step, model_type="micro")
#                 obs = obs.squeeze()

#                 # Extract 'close' price as 'expected_price'
#                 expected_price = obs['close']

#                 # Append 'expected_price' along with other observations
#                 obs_dict = {col: obs[col] for col in state_cols}
#                 obs_dict['expected_price'] = expected_price  # Add expected_price from close price
#                 observations.append(obs_dict)  # Store the observation as a dictionary

#                 obs = obs[state_cols]
#                 done, info = env.step(action)

#                 if done:
#                     break

#         #print(f'Observations for Micro: {observations}')
#         micro_input = pd.DataFrame(observations)
#         trades = env.render()

#         trades = pd.DataFrame(trades)
#         micro_input["shares"] = trades['shares'].values
#         return trades, micro_input

