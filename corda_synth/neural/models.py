"""
models.py — PyTorch HiFi-GAN Vocoder Architecture
=================================================
This defines the Generator network for the Neural Vocoder (Phase 4).
It takes the synthesized DSP audio or mel-spectrograms from the Corda
engine and upsamples/enhances them into human-quality waveforms using
Multi-Receptive Field Fusion (MRF) and transposed convolutions.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F

class ResBlock(nn.Module):
    def __init__(self, channels, kernel_size, dilation):
        super().__init__()
        self.convs1 = nn.ModuleList([
            nn.Conv1d(channels, channels, kernel_size, 1, dilation=d,
                      padding=(kernel_size*d - d)//2)
            for d in dilation
        ])
        self.convs2 = nn.ModuleList([
            nn.Conv1d(channels, channels, kernel_size, 1, dilation=1,
                      padding=(kernel_size - 1)//2)
            for _ in dilation
        ])

    def forward(self, x):
        for c1, c2 in zip(self.convs1, self.convs2):
            xt = F.leaky_relu(x, 0.1)
            xt = c1(xt)
            xt = F.leaky_relu(xt, 0.1)
            xt = c2(xt)
            x = xt + x
        return x

class HiFiGANGenerator(nn.Module):
    """
    Takes a conditioning vector (e.g. 80-band mel-spectrogram or the raw 
    DSP output from Corda's Phase 3) and decodes it into high-fidelity audio.
    """
    def __init__(self, initial_channel=512, resblock_kernel_sizes=[3, 7, 11],
                 resblock_dilation_sizes=[[1, 3, 5], [1, 3, 5], [1, 3, 5]],
                 upsample_rates=[8, 8, 2, 2], upsample_kernel_sizes=[16, 16, 4, 4],
                 input_channels=80): # 80 for mel-spectrogram conditioning
        super().__init__()
        self.num_kernels = len(resblock_kernel_sizes)
        self.num_upsamples = len(upsample_rates)
        self.conv_pre = nn.Conv1d(input_channels, initial_channel, 7, 1, padding=3)

        self.ups = nn.ModuleList()
        for i, (u, k) in enumerate(zip(upsample_rates, upsample_kernel_sizes)):
            self.ups.append(nn.ConvTranspose1d(
                initial_channel // (2 ** i),
                initial_channel // (2 ** (i + 1)),
                k, u, padding=(k - u) // 2
            ))

        self.resblocks = nn.ModuleList()
        for i in range(len(self.ups)):
            ch = initial_channel // (2 ** (i + 1))
            for j, (k, d) in enumerate(zip(resblock_kernel_sizes, resblock_dilation_sizes)):
                self.resblocks.append(ResBlock(ch, k, d))

        self.conv_post = nn.Conv1d(ch, 1, 7, 1, padding=3)

    def forward(self, x):
        # x is (Batch, Channels, Time)
        x = self.conv_pre(x)
        for i in range(self.num_upsamples):
            x = F.leaky_relu(x, 0.1)
            x = self.ups[i](x)
            xs = None
            for j in range(self.num_kernels):
                if xs is None:
                    xs = self.resblocks[i * self.num_kernels + j](x)
                else:
                    xs += self.resblocks[i * self.num_kernels + j](x)
            x = xs / self.num_kernels
        x = F.leaky_relu(x)
        x = self.conv_post(x)
        x = torch.tanh(x)
        return x
