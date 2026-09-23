import numpy as np
import pandas as pd


import warnings
warnings.filterwarnings('ignore')



# Update this as per the latest data
# dataFilePath = "aapl-merged.csv"


class Alpha:
    def __init__(self,dataFilePath):
        self.data = pd.read_csv(dataFilePath)
        self.data['ts_event'] = pd.to_datetime(self.data['ts_event'])

        self.stochasticAlpha = pd.DataFrame()
        self.determinedAlpha = pd.DataFrame()
        self.alphaPrime = pd.DataFrame()

        self.alphaDoublePrime = pd.DataFrame()

        self.mu  = pd.DataFrame()

        self.alpha0 = 0
    @staticmethod
    def format_determined_output(data,calculated_prices):
        """
        Formats the determined strategy output into a readable DataFrame.
        Args:
            data (pd.DataFrame): Original financial data with `ts_event` and `price`.
            calculated_prices (dict): Output of the determined_strategy function.

        Returns:
            pd.DataFrame: Readable DataFrame with `Datetime` and `Alpha`.
        """
        # Ensure the original data is datetime formatted
        data['ts_event'] = pd.to_datetime(data['ts_event'], errors='coerce')
        data = data.dropna(subset=['ts_event'])
        data['date'] = data['ts_event'].dt.date
        data['time'] = data['ts_event'].dt.time

        # Flatten the dictionary into a DataFrame
        readable_output = []
        for date, prices in calculated_prices.items():
            times = data[data['date'] == date]['time'].tolist()
            readable_output.extend([(f"{date} {t}", p) for t, p in zip(times, prices)])

        # Create DataFrame
        output_df = pd.DataFrame(readable_output, columns=['Datetime', 'Alpha'])
        return output_df


    # TODO : Need to introduce randomness inside stochastic strategy
    def alpha_estimation_stochastic_strategy(self, n=22):
 
        """
        Function to estimate stochastic alpha.
        Args:
            access data variable from class.
            n (int): Number of days to average for closing prices. By default, 22.
        Processing: Updates self.stochasticAlpha
        
        No Return -> Just Updates self.stochasticAlpha
        """
        # Extract date and time components
        self.data['date'] = self.data['ts_event'].dt.date
        self.data['time'] = self.data['ts_event'].dt.time

        # Filter the data to keep only rows between 9:00 AM and 4:30 PM
        start_time = pd.to_datetime('13:30:00').time()
        end_time = pd.to_datetime('20:00:00').time()
        filtered_data = self.data[(self.data['time'] >= start_time) & (self.data['time'] <= end_time)]

        # Get the closing price for each date
        closing_prices = filtered_data[filtered_data['time'] == end_time].set_index('date')['price']

        # Calculate rolling average of closing prices
        rolling_avg = closing_prices.rolling(window=n, min_periods=1).mean()

        # Calculate the new prices for each date
        def calculate_difference(row):
            return row['price'] - rolling_avg.get(row['date'], np.nan)

        filtered_data.loc[:, 'calculated_price'] = filtered_data.apply(calculate_difference, axis=1)

        # Aggregate results by date
        result = filtered_data.groupby('date')['calculated_price'].apply(list).to_dict()

        self.stochasticAlpha = self.format_determined_output(self.data,result)

    # Outdated Alpha Determined Strategy
    # def alpha_estimation_determined_strategy(self):
    #     """ 
    #     Function to estimate determined alpha.
    #     Args:
    #         data (pd.DataFrame): Financial data with 'ts_event' and 'price' columns.

    #     No Return -> Just Updates self.determinedAlpha variable
    #     """
    #     # Extract date and time components
    #     self.data['date'] = self.data['ts_event'].dt.date
    #     self.data['time'] = self.data['ts_event'].dt.time

    #     # Filter the data to keep only rows between 9:00 AM and 4:30 PM
    #     start_time = pd.to_datetime('13:30:00').time()
    #     end_time = pd.to_datetime('20:00:00').time()
    #     filtered_data = self.data[(self.data['time'] >= start_time) & (self.data['time'] <= end_time)]

    #     # Get the closing price for each date
    #     closing_prices = filtered_data[filtered_data['time'] == end_time].set_index('date')['price']

    #     # Calculate the new prices for each date
    #     def calculate_difference(row):
    #         return row['price'] - closing_prices.get(row['date'], np.nan)

    #     filtered_data.loc[:, 'calculated_price'] = filtered_data.apply(calculate_difference, axis=1)

    #     # Aggregate results by date
    #     result = filtered_data.groupby('date')['calculated_price'].apply(list).to_dict()
        
    #     tempData = self.data
    #     self.determinedAlpha = self.format_determined_output(tempData,result)

    #     pass

    # Updated Alpha Determined Strategy
    def ALPHA_determined_strategy(self,data):
        """
        Function to estimate alpha.
        Args:
            data (pd.DataFrame): Financial data with 'ts_event' and 'price' columns.

        Returns:
            dict: Keys as dates and values as calculated price differences.
        """
        # Extract date and time components
        data['date'] = data['ts_event'].dt.date
        data['time'] = data['ts_event'].dt.time

        # Get the closing price for each date
        end_time = pd.to_datetime('20:00:00').time()
        
        filtered_data = data
        # closing_prices = filtered_data[filtered_data['time'] == end_time].set_index('date')['unperturbed_price']

        def time_to_minutes(t):
            return t.hour * 60 + t.minute

        # Get the last price within some tolerance of market close
        def get_closing_prices(data):
            end_minutes = time_to_minutes(end_time)
            return data.groupby('date').apply(
                lambda x: x.iloc[(abs(x['time'].apply(time_to_minutes) - end_minutes)).argsort()[:1]]['unperturbed_price'].iloc[0]
            )
        closing_prices = get_closing_prices(filtered_data)
        

        def calculate_difference(row):
            return row['unperturbed_price'] - closing_prices.get(row['date'], np.nan)
        
        filtered_data['determined_alpha'] = filtered_data.apply(calculate_difference, axis=1)
        filtered_data.drop('date', axis=1, inplace=True)
        filtered_data.drop('time', axis=1, inplace=True)

        self.determinedAlpha = filtered_data

        pass

    def calc_alpha_prime(self,df):
        """
        Calculates the rate of change of Alpha with respect to time and adds it as a new column.

        Args:
            df (pd.DataFrame): DataFrame containing 'Datetime' and 'Alpha' columns.

        Returns:
            pd.DataFrame: DataFrame with an additional 'Alpha Prime' column.
        """
        
        # Ensure the 'Datetime' column is in datetime format
        df['Datetime'] = pd.to_datetime(df['Datetime'], errors='coerce')

        # Drop rows with invalid Datetime values (if any)
        df = df.dropna(subset=['Datetime']).reset_index(drop=True)

        # Sort the DataFrame by 'Datetime' to ensure correct ordering
        df = df.sort_values(by='Datetime').reset_index(drop=True)

        # Calculate the difference in Alpha values and time in seconds
        df['Alpha Difference'] = df['Alpha'].diff()
        df['Time Difference'] = df['Datetime'].diff().dt.total_seconds()

        # Calculate Alpha Prime (rate of change of Alpha)
        df['Alpha_Prime'] = df['Alpha Difference'] / df['Time Difference']

        # Set the first value of Alpha Prime to 0 as specified
        df.loc[0, 'Alpha_Prime'] = 0

        # Drop the intermediate columns
        df.drop(columns=['Alpha Difference', 'Time Difference','Alpha'], inplace=True)

        self.alphaPrime = df



    def calculate_mu(self):
        """
            Input : Uses the self.alphaPrime variable from the class
            Processing : Calculates Mu
            Output : Updates self.mu variable
        """
        mu_local = self.alphaPrime.copy(deep=True)
        mu_local['Mu'] = -1*mu_local.loc[:,'Alpha_Prime']
        mu_local.drop(columns=['Alpha_Prime'], inplace=True)
        self.mu = mu_local


    def calculate_alpha_double_prime(self):
        '''
            input: calls self.alphaPrime
            processing: calculates alpha double prime (derivative) of alpha prime 
            output: data frame of alpha double primes
        '''

        df = self.alphaPrime

        # Ensure the 'Datetime' column is in datetime format
        df['Datetime'] = pd.to_datetime(df['Datetime'], errors='coerce')

        # Drop rows with invalid Datetime values (if any)
        df = df.dropna(subset=['Datetime']).reset_index(drop=True)

        # Sort the DataFrame by 'Datetime' to ensure correct ordering
        df = df.sort_values(by='Datetime').reset_index(drop=True)

        # Calculate the difference in Alpha Prime values and time in seconds
        df['Alpha_Prime_Difference'] = df['Alpha_Prime'].diff()
        df['Time Difference'] = df['Datetime'].diff().dt.total_seconds()

        # Calculate Alpha Double Prime (rate of change of Alpha Prime)
        df['Alpha_Double_Prime'] = df['Alpha_Prime_Difference'] / df['Time Difference']

        # Set the first value of Alpha Double Prime to 0 as specified
        df.loc[0, 'Alpha_Double_Prime'] = 0

        # Drop the intermediate columns
        df.drop(columns=['Alpha_Prime_Difference', 'Time Difference','Alpha_Prime'], inplace=True)

        self.alphaDoublePrime = df

        

    def run(self, alphaStrategyType):
        """
            Input : Takes the String Input "Stochastic" or "Deterministic"
            Processing : Performs the relevant functions as per chosen alpha strategy
            Output : Returns pertinent variables as per chosen alpha strategy
        """


        try : 
            # For Stochastic Strategy
            if alphaStrategyType.lower() == "stochastic":
                self.alpha_estimation_stochastic_strategy()
                self.alpha0 = self.stochasticAlpha.loc[0, 'Alpha']
                self.calc_alpha_prime(self.stochasticAlpha)
                self.calculate_mu()
                return (self.stochasticAlpha,self.mu)
            
            # For Deterministic Strategy
            elif alphaStrategyType.lower() == "deterministic":                          
                self.alpha_estimation_determined_strategy()
                self.alpha0 = self.determinedAlpha.loc[0,"Alpha"]
                self.calc_alpha_prime(self.determinedAlpha)
                self.calculate_alpha_double_prime()
                return (self.determinedAlpha,self.alpha0,self.alphaPrime,self.alphaDoublePrime)
            else:
                raise ValueError("Invalid Alpha Strategy")
        except Exception as e:
           raise RuntimeError(e)