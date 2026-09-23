import torch
import torch.nn as nn
import torch.nn.functional as F
from stable_baselines3.common.torch_layers import BaseFeaturesExtractor
from stable_baselines3 import PPO
from stable_baselines3.common.policies import ActorCriticPolicy
from gym import spaces


class UNetTransformerEncoder(nn.Module):
    def __init__(self, in_channels, out_channels,features_dim):
        super(UNetTransformerEncoder, self).__init__()
        self.in_channels = in_channels
        self.out_channels = out_channels
        self.features_dim = features_dim

        # Define U-Net layers
        self.encoder1 = self._block(in_channels, 64)
        self.encoder2 = self._block(64, 128)
        self.encoder3 = self._block(128, 256)
        self.encoder4 = self._block(256, 512)
        self.bottleneck = self._block(512, 1024)
        self.decoder4 = self._block(1024 + 512, 512)
        self.decoder3 = self._block(512 + 256, 256)
        self.decoder2 = self._block(256 + 128, 128)
        self.decoder1 = self._block(128 + 64, out_channels)

        self.encoder_layer = nn.TransformerEncoderLayer(d_model=features_dim, nhead=8, dropout=0.1)
        self.transformer_encoder = nn.TransformerEncoder(self.encoder_layer, num_layers=6)


    def _block(self, in_channels, out_channels):
        return nn.Sequential(
            nn.Conv1d(in_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm1d(out_channels),
            nn.ReLU(inplace=True),
            nn.Conv1d(out_channels, out_channels, kernel_size=3, padding=1),
            nn.BatchNorm1d(out_channels),
            nn.ReLU(inplace=True)
        )

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
    def __init__(self, observation_space: spaces.Box, features_dim = 256):
        super(CustomUNetTransformerModel, self).__init__(observation_space, features_dim)
        self.embedding = nn.Linear(observation_space.shape[0], features_dim)  # Adapt the input size if necessary
        self.unet_transformer = UNetTransformerEncoder(1, features_dim,features_dim)  # Pass features_dim correctly

    def forward(self, observations: torch.Tensor) -> torch.Tensor:
        x = self.embedding(observations)
        x = x.unsqueeze(1)  # Add channel dimension
        x = self.unet_transformer(x)
        x = x.mean(dim=2)  # Global average pooling
        return x


class CustomTransformerPolicy(ActorCriticPolicy):
    def __init__(self, observation_space, action_space, lr_schedule, *args, **kwargs):
        features_dim = 256  # Define features_dim here or pass it dynamically
        super(CustomTransformerPolicy, self).__init__(observation_space, action_space, lr_schedule, 
                                                      features_extractor_class=CustomUNetTransformerModel, 
                                                      features_extractor_kwargs={'features_dim': features_dim},
                                                      *args, **kwargs)