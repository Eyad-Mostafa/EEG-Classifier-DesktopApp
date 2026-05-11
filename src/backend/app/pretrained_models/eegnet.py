import torch
import torch.nn as nn

class EEGNet(nn.Module):
    def __init__(self, num_channels=2, num_classes=2, dropout_rate=0.2):
        super(EEGNet, self).__init__()

        # Number of samples is fixed according to the JSON config (15 sec * 100 Hz = 1500)
        num_samples = 1500

        # =====================================
        # BLOCK 1
        # Temporal Convolution
        # =====================================
        self.block1 = nn.Sequential(
            nn.Conv2d(
                in_channels=1,
                out_channels=8,
                kernel_size=(1, 64),
                padding=(0, 32),
                bias=False,
            ),
            nn.BatchNorm2d(8),
            # Depthwise Convolution
            nn.Conv2d(
                in_channels=8,
                out_channels=16,
                kernel_size=(num_channels, 1),
                groups=8,
                bias=False,
            ),
            nn.BatchNorm2d(16),
            nn.ELU(),
            nn.AvgPool2d(kernel_size=(1, 4)),
            nn.Dropout(dropout_rate),
        )

        # =====================================
        # BLOCK 2
        # Separable Convolution
        # =====================================
        self.block2 = nn.Sequential(
            nn.Conv2d(
                in_channels=16,
                out_channels=16,
                kernel_size=(1, 16),
                padding=(0, 8),
                groups=16,
                bias=False,
            ),
            nn.Conv2d(in_channels=16, out_channels=16, kernel_size=(1, 1), bias=False),
            nn.BatchNorm2d(16),
            nn.ELU(),
            nn.AvgPool2d(kernel_size=(1, 8)),
            nn.Dropout(dropout_rate),
        )

        # =====================================
        # CLASSIFIER
        # =====================================
        self.flatten_size = self.calculate_flatten_size(num_channels, num_samples)

        # The loaded model expects 1 output neuron for BCEWithLogitsLoss
        self.classifier = nn.Sequential(nn.Flatten(), nn.Linear(self.flatten_size, 1))

    def calculate_flatten_size(self, num_channels, num_samples):
        x = torch.randn(1, 1, num_channels, num_samples)
        x = self.block1(x)
        x = self.block2(x)
        flatten_size = x.view(1, -1).shape[1]
        return flatten_size

    def forward(self, x):
        # input shape: (batch, channels, samples)
        x = x.unsqueeze(1)
        # becomes: (batch, 1, channels, samples)

        x = self.block1(x)
        x = self.block2(x)
        
        # logit shape: (batch, 1)
        logit = self.classifier(x)
        
        # Multi-class adapter: Backend uses Softmax. 
        # For Softmax to work like Sigmoid for binary classes:
        # P(class 1) = exp(logit) / (exp(0) + exp(logit)) = sigmoid(logit)
        # P(class 0) = exp(0) / (exp(0) + exp(logit)) = 1 - sigmoid(logit)
        # Therefore, we output [0, logit] for the two classes.
        out = torch.cat([torch.zeros_like(logit), logit], dim=1)
        
        return out
