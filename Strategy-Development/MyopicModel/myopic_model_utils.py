# Loading the necessary libraries
import pandas as pd
import numpy as np
from alpha_utils import Alpha
from lambda_utils import LambdaEstimation
import matplotlib.dates as mdates
import matplotlib.pyplot as plt


# TODO : Am not calling it for now , in case future improvements is needed. For now I just hardcoded the value
from beta_utils import calculate_beta

class MyopicOptimizationModel :
  def __init__(self,inputTradingData,inventory,datasetFilePath,T,N):


    # TRADING SPECIFIC VARIABLES STARTING FROM HERE ----------------------

    self.T = T                  # Time Horizon
    self.N = N                  # Number of Buckets


    # inputTradingData is the input trading data that the model would take
    # Defining Trade Variables
    self.trading_data = inputTradingData
    self.trades_executed = []
    self.Q0 = inventory                 
    self.inventory_left - self.inventory - np.sum(self.trades_executed)   # Current Inventory




    # Dataset File Path Needed for Alpha,Beta,Lambda Estimation
    self.datasetFilePath = datasetFilePath



    # ESTIMATION VARIABLES STARTING FROM HERE ----------------------

    self.beta = 0.6931471805599453

    self.lam = 0

    # Alpha Variables will be modified as per estimation function
    self.stochasticAlpha = pd.DataFrame()
    self.determinedAlpha = pd.DataFrame()
    self.alpha0 = 0 

    self.alphaPrime = pd.DataFrame()
    self.alphaDoublePrime = pd.DataFrame()

    self.mu  = pd.DataFrame()
    self.mu0 = 0



    # OUTPUT VARIABLES STARTING FROM HERE -------------------------
    self.nu = 0
    self.qStar = [self.Q0]
    self.qStarPrime = []

    self.PnLTable = pd.DataFrame()


    # Common
    self.output = {}

  def calculate_lam(self):
    """
      Input : Dataset containing previous months data for estimating lambda for the day
      Processing : Call Lambda Estimation Class and compute lambda
      Output : -> This would output lambda, which will be stored in an array
    """

    lamEstimation = LambdaEstimation(self.datasetFilePath)
    self.lam = lamEstimation.getLam()
    
  def calculate_determined_alpha(self):

    """
      Output : -> For now im assuming this would calculate alpha,alpha_prime,alpha_SecondPrime
    """
    

    alphaStrategy = Alpha(self.datasetFilePath)
    self.determinedAlpha,self.alpha0,self.alphaPrime,self.alphaDoublePrime = alphaStrategy.run("deterministic")

  def calculate_stochastic_alpha(self):

    """

      Output : -> For now im assuming this would calculate alpha,alpha_prime,alpha_SecondPrime
    """
    
    alphaStrategy = Alpha(self.datasetFilePath)
    self.stochasticAlpha,self.mu = alphaStrategy.run("stochastic")
    self.mu0 = self.mu.loc[0,"Mu"]


  def execDeterminedAlphaQ(self):

    for t in range(self.T):
      self.nu = -1* (2*self.lam* self.Q0 + self.alpha0 + self.beta*np.sum(self.determinedAlpha))/(2 + self.beta*self.T)
      Q_star_prime = (self.beta*(self.determinedAlpha[t]-self.alphaDoublePrime*self.beta**(-2) + self.beta*self.nu ))/(2*self.lam)
      Q_star = self.Q0 + (self.beta*(np.sum[self.determinedAlpha[:t]]))/(2*self.lam) + (self.beta*(t*self.nu - self.alphaPrime + self.alphaPrime0))/(2*self.lam)

      self.qStar.append(Q_star)
      self.qStarPrime.append(Q_star_prime)
    self.output = {"Q_Star" : self.qStar,"Q_star_Prime" : self.qStarPrime}

    

  def execStochasticAlphaQ(self):

    # TODO : Need to clarify if we have to consider the the entire time horizon in the for loop or just till range t+1(for i in range(t+1))

    for t in range(self.T):
      currAlphaArray = self.stochasticAlpha[:t]
      currMuArray = self.mu[:t]
      currAlphaArray *= self.beta
      currX = np.array(currAlphaArray) + np.array(currMuArray)

      delT = self.T/self.N

      Qt_star = self.Q0 + (np.sum(currX))*delT/(2*self.lam) + (self.stochasticAlpha[t] + (self.mu[t] * self.beta**(-1)) - self.alpha0 - (self.mu0 * self.beta**(-1)))/(2*self.lam)

      self.qStar.append(Qt_star)
    self.output = {"Q_Star" : self.qStar}

  
  def executeModel(self,alphaStrategyInput):
    try :
      self.calculate_lam()
      if alphaStrategyInput.lower() == "deterministic":
        self.calculate_determined_alpha()
        self.execDeterminedAlphaQ()
        return self.output
      elif alphaStrategyInput.lower() == "stochastic":
        self.calculate_stochastic_alpha()
        self.execStochasticAlphaQ()
        return self.output
      else:
          raise ValueError("Invalid Alpha Strategy")
    except Exception as e:
        return f"Error : {e}"
    

  def PnL(self,data,beta,lambda_t):
    """
    Function to add column PnL.
    Args:
        data (pd.DataFrame): Financial data with 'ts_event' and 'determined_alpha' columns.
    Returns:
        pd.DataFrame: Original data with a new 'determined_nu' column.
    """
    data = data.copy()  # Avoid modifying the original DataFrame
    data['date'] = data['ts_event'].dt.date
    data['time'] = data['ts_event'].dt.time
    start_time = pd.to_datetime('13:30:00').time()
    end_time = pd.to_datetime('20:00:00').time()
    
    def calculate_optimal_PnL(group):
        # Get 'determined_alpha' at start_time
        res = ((group['determined_alpha'] - group['I_star_t']) * group['delta_Q_star']).cumsum()
        return res
    
    def calculate_PnL(group):
        # Get 'determined_alpha' at start_time
        res = ((group['determined_alpha'] - group['price_impact']) * group['delta_Q']).cumsum()
        return res

    def calculate_integral_test_1(group):
        res = ((group['determined_alpha'] - group['price_impact']) * (beta*group['price_impact']+group['I_prime'])).cumsum()
        res = res/lambda_t
        return res

    def calculate_integral_test_1_optimal(group):
        res = ((group['determined_alpha'] - group['I_star_t']) * (beta*group['I_star_t']+group['I_star_prime'])).cumsum()
        res = res/lambda_t
        return res
        

    def calculate_integral(group):
        a=group['myopic_market_obj'].sum() + group[group['time'] == end_time]['determined_alpha'] * group[group['time'] == end_time]['price_impact']
        a=a-(group[group['time'] == end_time]['price_impact'])**2/2
        a=a/lambda_t
        return a
    
    def calculate_optimal_integral(group):
        a=group['myopic_opt_obj'].sum()+group[group['time'] == end_time]['determined_alpha'] * group[group['time'] == end_time]['I_star_t']
        a=a-(group[group['time'] == end_time]['I_star_t'])**2/2
        a=a/lambda_t
        return a

    def calculate_optimal_position(group):
        summed_alpha = group['determined_alpha'].sum()
        if group[group['time'] == start_time].empty:
            Q0 = 0  # Default value
        else:
            Q0 = -1 * (group[group['time'] == start_time]['determined_alpha'].iloc[0] + beta * summed_alpha) / (2 * lambda_t)
        Q0_vector = np.full(len(group), Q0)
        a = Q0_vector + group['delta_Q_star'].cumsum()
        return a
        
    def calculate_vwap(group):
        VWAP = (group['bid_fill'] + group['ask_fill'])/((group['bid_fill']+group['ask_fill']).sum())
        summed_alpha = group['determined_alpha'].sum()
        if group[group['time'] == start_time].empty:
            Q0 = 0  # Default value
        else:
            Q0 = -1 * (group[group['time'] == start_time]['determined_alpha'].iloc[0] + beta * summed_alpha) / (2 * lambda_t)
        Q0_vector = np.full(len(group), Q0)
        position_vwap = Q0_vector - Q0_vector * VWAP.cumsum()
        return position_vwap
    def calculate_vwap_delta_Q(group):
        res = group['vwap_position'].diff().fillna(0)
        return res
    def calculate_vwap_price_impact(group):
        I = [0]  
        for t in range(1, len(group)): 
            I_next = I[-1] - I[-1] * beta + lambda_t * group.iloc[t]['vwap_delta_Q']
            I.append(I_next) 
        return pd.Series(I, index=group.index)
        
    def calculate_vwap_PnL(group):
        res = ((group['determined_alpha'] - group['vwap_I']) * group['vwap_delta_Q']).cumsum()
        return res
     

    def calculate_twap(group):
        TWAP = np.full(len(group), 1)/len(group)
        summed_alpha = group['determined_alpha'].sum()
        if group[group['time'] == start_time].empty:
            Q0 = 0  # Default value
        else:
            Q0 = -1 * (group[group['time'] == start_time]['determined_alpha'].iloc[0] + beta * summed_alpha) / (2 * lambda_t)
        Q0_vector = np.full(len(group), Q0)
        position_twap = Q0_vector - Q0_vector * TWAP.cumsum()
        return pd.Series(position_twap, index=group.index)
    def calculate_twap_delta_Q(group):
        res = group['twap_position'].diff().fillna(0)
        return res
    def calculate_twap_price_impact(group):
        I = [0]
        for t in range(1, len(group)):  
            I_next = I[-1] - I[-1] * beta + lambda_t * group.iloc[t]['twap_delta_Q']
            I.append(I_next)
        return pd.Series(I, index=group.index)

    def calculate_twap_PnL(group):
        res = ((group['determined_alpha'] - group['twap_I']) * group['twap_delta_Q']).cumsum()
        return res    
        
    
    data['optimal_PnL'] = data.groupby('date').apply(calculate_optimal_PnL,include_groups=False).reset_index(level=0, drop=True)
    data['PnL'] = data.groupby('date').apply(calculate_PnL,include_groups=False).reset_index(level=0, drop=True)
    data['integral'] = data.groupby('date').apply(calculate_integral,include_groups=False).reset_index(level=0, drop=True)
    data['optimal_integral'] = data.groupby('date').apply(calculate_optimal_integral,include_groups=False).reset_index(level=0, drop=True)
    data['integral_test1'] = data.groupby('date').apply(calculate_integral_test_1,include_groups=False).reset_index(level=0, drop=True)
    data['integral_test1_opt'] = data.groupby('date').apply(calculate_integral_test_1_optimal,include_groups=False).reset_index(level=0, drop=True)
    data['optimal_position'] = data.groupby('date').apply(calculate_optimal_position,include_groups=False).reset_index(level=0, drop=True)
    data['vwap_position'] = data.groupby('date').apply(calculate_vwap, include_groups=False).reset_index(level=0, drop=True)
    data['vwap_delta_Q'] = data.groupby('date').apply(calculate_vwap_delta_Q, include_groups=False).reset_index(level=0, drop=True)
    data['vwap_I'] = data.groupby(data['date']).apply(calculate_vwap_price_impact,include_groups=False).reset_index(level=0, drop=True)
    data['vwap_PnL'] = data.groupby('date').apply(calculate_vwap_PnL, include_groups=False).reset_index(level=0, drop=True)
    data['twap_position'] = data.groupby('date').apply(calculate_twap,include_groups=False).reset_index(level=0, drop=True)
    data['twap_delta_Q'] = data.groupby('date').apply(calculate_twap_delta_Q, include_groups=False).reset_index(level=0, drop=True)
    data['twap_I'] = data.groupby(data['date']).apply(calculate_twap_price_impact,include_groups=False).reset_index(level=0, drop=True)
    data['twap_PnL'] = data.groupby('date').apply(calculate_twap_PnL, include_groups=False).reset_index(level=0, drop=True)
    # Clean up
    data.drop(['date', 'time'], axis=1, inplace=True)
    self.PnLTable = data

    pass

  def plotTradeStrategies(self):
    res = self.PnLTable
    res['ts_event'] = pd.to_datetime(res['ts_event'])
    res['date'] = res['ts_event'].dt.date

    # Get the list of unique dates and select the first 6 days
    unique_dates = res['date'].unique()
    first_6_days = unique_dates[:12]

    # Filter the DataFrame to include only the first 6 days
    filtered_res = res[res['date'].isin(first_6_days)].copy()

    # Sort the data by 'ts_event' within each day
    filtered_res.sort_values(['date', 'ts_event'], inplace=True)

    # Prepare for plotting
    num_days = len(first_6_days)
    nrows = 4
    ncols = 3

    fig, axes = plt.subplots(nrows=nrows, ncols=ncols, figsize=(18, 16))
    axes = axes.flatten()  # Flatten the axes array for easy indexing

    # Loop over each day and plot the time series
    for i, date in enumerate(first_6_days):
        # Get the data for the current day
        day_data = filtered_res[filtered_res['date'] == date]
        
        # Plotting

        ax = axes[i]
        ax.plot(day_data['ts_event'], day_data['optimal_position'], label='Myopic Trade Process')
        ax.plot(day_data['ts_event'], day_data['vwap_position'], label='VWAP Trade Process')
        ax.plot(day_data['ts_event'], day_data['twap_position'], label='TWAP Trade Process')
        
        
        # Formatting the x-axis to show time only
        ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        ax.set_xlabel('Time')
        ax.set_ylabel('Position')
        ax.set_title(f'Date: {date}')
        ax.legend()
        ax.grid(True)
        
        # # Rotate x-axis labels if needed
        plt.setp(ax.get_xticklabels(), rotation=45, ha='right')

    # Hide any unused subplots if there are any
    for j in range(i+1, nrows * ncols):
        fig.delaxes(axes[j])

    plt.tight_layout()
    plt.show()

    pass
