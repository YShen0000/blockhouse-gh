import torch
import torch.nn as nn
import torch.nn.functional as F
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from stable_baselines3 import PPO
from stable_baselines3.common.policies import ActorCriticPolicy
from gym import spaces
from pytorch_widedeep.models import TabTransformer




PPO_MODEL_BEST_PARAMS = {'learning_rate': 0.0009931989008886031, 'n_steps': 512, 'batch_size': 128, 
                        'gamma': 0.9916829193042708, 'clip_range': 0.21127653449387027, 'n_epochs': 6, 'ent_coef': 0.1, 'verbose': 0}

PPO_MODEL_BEST_PARAMS_TAB = {'learning_rate': 0.0179457, 'n_steps': 128, 'batch_size': 128,
                        'gamma': 0.951791, 'clip_range': 0.128042, 'n_epochs': 8, 'ent_coef': 0.0002526, 'verbose': 1}


"""
## Transformer Initialization - U-Net Architecture

### Class Summary

**`UNetTransformerEncoder`**

This class implements a hybrid architecture combining a U-Net style encoder-decoder with a Transformer encoder. It is designed to handle different scenarios (e.g., small, medium, large) by adjusting the parameters of the Transformer layers dynamically.

### Key Components

- **U-Net Layers:**
  - **Encoders (`encoder1`, `encoder2`, `encoder3`, `encoder4`)**: Sequential layers that reduce the input dimensionality while capturing hierarchical features.
  - **Bottleneck:** A central layer that captures the most abstract representation before upsampling.
  - **Decoders (`decoder4`, `decoder3`, `decoder2`, `decoder1`)**: Layers that upsample the feature maps back to the original resolution while combining features from corresponding encoder layers.

- **Transformer Layers:**
  - **Scenario-based Transformer Encoder Layer (`encoder_layer`)**: The Transformer encoder layer is configured based on the specified scenario. Different scenarios adjust the number of heads and dropout rates in the Transformer.
  - **Transformer Encoder (`transformer_encoder`)**: Applies multiple Transformer encoder layers to the output of the U-Net decoders, allowing the model to capture long-range dependencies in the feature maps.

### Scenarios

- **small:** 4 heads, 0.2 dropout
- **small-medium:** 8 heads, 0.15 dropout
- **medium:** 8 heads, 0.1 dropout
- **medium-large:** 16 heads, 0.08 dropout
- **large:** 32 heads, 0.05 dropout

### Market Cap

- **large:** 
- **medium:** 
- **small:**

### Parameters

- **`in_channels (int)`**: Number of input channels for the U-Net.
- **`out_channels (int)`**: Number of output channels for the U-Net.
- **`scenario (str)`**: Scenario to configure the Transformer layers (default is 'medium').

### Methods

- **`_block(self, in_channels, out_channels)`**: Defines a convolutional block with Conv1D, BatchNorm, and ReLU activation.
- **`_get_encoder_layer(self, features_dim, scenario)`**: Configures the Transformer encoder layer based on the scenario.
- **`forward(self, x)`**: Passes the input through the U-Net encoder-decoder architecture followed by the Transformer encoder.

"""


class UNetTransformerEncoder(nn.Module):
    def __init__(self, in_channels, out_channels, scenario='medium', market_cap="large"):
        """
        Args:
            in_channels: int
                Number of input channels
            out_channels: int
                Number of output channels
            scenario: str
                Scenario to be used
            cap: str
                Market cap to be used (large, medium, small)

        """
        
        super(UNetTransformerEncoder, self).__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.scenario = scenario

        # Define U-Net layers
        self._build_unet_model(in_channels, out_channels, market_cap=market_cap)

        # Define Transformer layers based on scenario
        self.encoder_layer = self._get_encoder_layer(out_channels, scenario)
        self.transformer_encoder = nn.TransformerEncoder(self.encoder_layer, num_layers=6)

    def _block(self, in_channels, out_channels, dilation = 1,  kernel_size = 3, padding = 1):
        return nn.Sequential(
            nn.Conv1d(in_channels, out_channels, kernel_size=3, padding=padding),
            nn.BatchNorm1d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv1d(out_channels, out_channels, kernel_size=3, padding=padding),
            nn.BatchNorm1d(out_channels),
            nn.ReLU(inplace=True)
        )
    
    # Dynamic weight change based on scenario
    def _get_encoder_layer(self, features_dim, scenario):
        if scenario == 'small':
            return nn.TransformerEncoderLayer(d_model=features_dim, nhead=4, dropout=0.2)
        elif scenario == 'small-medium':
            return nn.TransformerEncoderLayer(d_model=features_dim, nhead=8, dropout=0.15)
        elif scenario == 'medium':
            return nn.TransformerEncoderLayer(d_model=features_dim, nhead=8, dropout=0.1)
        elif scenario == 'medium-large':
            return nn.TransformerEncoderLayer(d_model=features_dim, nhead=16, dropout=0.08)
        elif scenario == 'large':
            return nn.TransformerEncoderLayer(d_model=features_dim, nhead=32, dropout=0.05)
        else:
            raise ValueError(f"Unknown scenario: {scenario}")
        
    def _build_unet_model(self, in_channels, out_channels, market_cap):
        if market_cap == "large":
            dilation_top_layers= 1
            kernel_size_top_layers = 3

            dilation_bottom_layers = 1
            kernel_size_bottom_layers = 3

        elif market_cap == "medium":
            dilation_top_layers= 1
            kernel_size_top_layers = 5

            dilation_bottom_layers = 1
            kernel_size_bottom_layers = 3

        elif market_cap == "small":
            dilation_top_layers= 1
            kernel_size_top_layers = 5

            dilation_bottom_layers = 1
            kernel_size_bottom_layers = 5

        else:
            raise ValueError(f"Unknown Market cap: {market_cap}")


        padding_top_layers = "same"  # int(round(dilation_top_layers * (kernel_size_top_layers - 1) / 2,0)) 
        padding_bottom_layers = "same"  # int (round(dilation_bottom_layers * (kernel_size_bottom_layers - 1) / 2,0))

        self.encoder1 = self._block(in_channels, 64, dilation=dilation_top_layers, kernel_size=kernel_size_top_layers, padding=padding_top_layers)
        self.encoder2 = self._block(64, 128, dilation=dilation_top_layers, kernel_size=kernel_size_top_layers, padding=padding_top_layers)
        self.encoder3 = self._block(128, 256, dilation=dilation_bottom_layers, kernel_size=kernel_size_bottom_layers, padding=padding_bottom_layers)
        self.encoder4 = self._block(256, 512, dilation=dilation_bottom_layers, kernel_size=kernel_size_bottom_layers, padding=padding_bottom_layers)
        self.bottleneck = self._block(512, 1024, )
        self.decoder4 = self._block(1024 + 512, 512, dilation=dilation_bottom_layers, kernel_size=kernel_size_bottom_layers, padding=padding_bottom_layers)
        self.decoder3 = self._block(512 + 256, 256, dilation =dilation_bottom_layers, kernel_size=kernel_size_bottom_layers, padding=padding_bottom_layers)
        self.decoder2 = self._block(256 + 128, 128)
        self.decoder1 = self._block(128 + 64, out_channels)


    def forward(self, x):
        enc1 = self.encoder1(x)
        enc2 = self.encoder2(F.max_pool1d(enc1, 2))
        enc3 = self.encoder3(F.max_pool1d(enc2, 2))
        enc4 = self.encoder4(F.max_pool1d(enc3, 2))

        bottleneck = self.bottleneck(F.max_pool1d(enc4, 2))

        dec4 = self.decoder4(torch.cat((F.interpolate(bottleneck, scale_factor=2), enc4), dim=1))
        dec3 = self.decoder3(torch.cat((F.interpolate(dec4, scale_factor=2), enc3), dim=1))
        dec2 = self.decoder2(torch.cat((F.interpolate(dec3, scale_factor=2), enc2), dim=1))
        dec1 = self.decoder1(torch.cat((F.interpolate(dec2, scale_factor=2), enc1), dim=1))

        # Transformer encoding
        x = self.transformer_encoder(dec1.permute(2, 0, 1)).permute(1, 2, 0)  # Permute for transformer encoder and back

        return x


class CustomUNetTransformerModel(BaseFeaturesExtractor):
    def __init__(self, observation_space: spaces.Box, features_dim: int = 256, scenario: str = 'medium', market_cap: str = 'large'):
        super(CustomUNetTransformerModel, self).__init__(observation_space, features_dim)
        self.embedding = nn.Linear(observation_space.shape[0], features_dim)  # Adapt the input size if necessary
        self.scenario = scenario
        self.unet_transformer = UNetTransformerEncoder(1, features_dim, scenario, market_cap)

    def forward(self, observations: torch.Tensor) -> torch.Tensor:
        x = self.embedding(observations)
        x = x.unsqueeze(1)
        x = self.unet_transformer(x)
        x = x.mean(dim=2)
        return x

class CustomTransformerPolicy(ActorCriticPolicy):
    def __init__(self, observation_space, action_space, lr_schedule, scenario='medium', market_cap='large', *args, **kwargs):
        super(CustomTransformerPolicy, self).__init__(observation_space, action_space, lr_schedule, 
                                                      features_extractor_class=CustomUNetTransformerModel, 
                                                      features_extractor_kwargs={'features_dim': 256, 'scenario': scenario, 'market_cap': market_cap},
                                                      *args, **kwargs)



class TabTransformerExtractor(BaseFeaturesExtractor):
    """
    Custom feature extractor using TabTransformer for processing tabular data.

    :param observation_space: (gym.Space) The observation space of the environment
    :param continuous_cols: List of continuous column names
    :param features_dim: (int) Number of features extracted (default: 256)
    """

    def __init__(self, observation_space: spaces.Box, continuous_cols, scenario, market_cap, features_dim: int = 256):
        super().__init__(observation_space, features_dim)

        if scenario == 'small':
            nhead = 4
            dropout = 0.2
        elif scenario == 'small-medium':
            nhead = 8
            dropout = 0.15
        elif scenario == 'medium':
            nhead = 8
            dropout = 0.1
        elif scenario == 'medium-large':
            nhead = 16
            dropout = 0.08
        elif scenario == 'large':
            nhead = 32
            dropout = 0.05
        else:
            raise ValueError(f"Unknown scenario: {scenario}")

        # Initialize TabTransformer
        self.tab_transformer = TabTransformer(
            column_idx={k: v for v, k in enumerate(continuous_cols)},
            embed_continuous=True,
            continuous_cols=continuous_cols,
            embed_continuous_method='standard',
            n_blocks=4,
            n_heads= nhead,
            attn_dropout= dropout,
            cont_norm_layer='layernorm',
            cont_embed_dropout=0.05
        )

        # Compute shape by doing one forward pass
        with torch.no_grad():
            n_flatten = self.tab_transformer.forward(
                torch.as_tensor(observation_space.sample()[None]).float()
            ).shape[1]

        # Define linear layer for final feature extraction
        self.linear = nn.Sequential(nn.Linear(n_flatten, features_dim), nn.GELU())

    def forward(self, observations: torch.Tensor) -> torch.Tensor:
        """
        Process the input observations through TabTransformer and linear layer.

        :param observations: (th.Tensor) Input observations
        :return: (th.Tensor) Processed features
        """
        return self.linear(self.tab_transformer(observations))


class TabTransformerPolicy(ActorCriticPolicy):
    def __init__(self, observation_space, action_space, lr_schedule, state_cols, scenario='medium', market_cap='large', *args, **kwargs):
        super(TabTransformerPolicy, self).__init__(observation_space, action_space, lr_schedule,
                                                      features_extractor_class=TabTransformerExtractor,
                                                      features_extractor_kwargs={'features_dim': 256, 'scenario': scenario, 'market_cap': market_cap, "continuous_cols": state_cols},
                                                      *args, **kwargs)


class MetaLearner:
    def __init__(self):
        # Define thresholds for different buckets
        self.small_threshold = 10
        self.small_medium_threshold = 100
        self.medium_threshold = 500
        self.medium_large_threshold = 2000
        self.large_threshold = 10000

        # Define Market Cap
        # self.

    def classify_scenario(self, transaction_size, timeframe=390):
        """
        Classify the scenario based on the transaction size.
        The default timeframe is set to 390 minutes (1 trading day).
        """
        if transaction_size < self.small_threshold:
            return 'small'
        elif self.small_threshold <= transaction_size < self.small_medium_threshold:
            return 'small-medium'
        elif self.small_medium_threshold <= transaction_size < self.medium_threshold:
            return 'medium'
        elif self.medium_threshold <= transaction_size < self.medium_large_threshold:
            return 'medium-large'
        elif self.medium_large_threshold <= transaction_size < self.large_threshold:
            return 'large'
        else:
            return 'large'

    def classify_market_cap(self, market_cap):
        """
        Classify the market cap based on the transaction size.
        """
        if market_cap < 2e9: # less than 2 billion
            return 'small'
        elif market_cap < 1e10: #less than 10 billion
            return 'medium'
        else:
            return 'large'

