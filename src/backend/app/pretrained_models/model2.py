import torch
import torch.nn as nn

class CNN_LSTM(nn.Module):
    def __init__(self, num_channels=16, num_classes=2):
        super(CNN_LSTM, self).__init__()

        # Fixed CNN architecture for input size 100
        self.cnn = nn.Sequential(
            # Block 1 - Reduce dimension
            nn.Conv1d(in_channels=num_channels, out_channels=64, kernel_size=5, stride=1, padding=2),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=2, stride=2),  # 100 -> 50
            
            # Block 2
            nn.Conv1d(in_channels=64, out_channels=128, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=2, stride=2),  # 50 -> 25
            
            # Block 3
            nn.Conv1d(in_channels=128, out_channels=256, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=2, stride=2),  # 25 -> 12
            
            # Block 4
            nn.Conv1d(in_channels=256, out_channels=256, kernel_size=3, stride=1, padding=1),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.AdaptiveAvgPool1d(8),  # Force output to 8 time points
        )

        # LSTM layers
        self.lstm1 = nn.LSTM(
            input_size=256,
            hidden_size=128,
            batch_first=True,
            dropout=0.3,
            bidirectional=True
        )

        self.lstm2 = nn.LSTM(
            input_size=256,  # 128*2 for bidirectional
            hidden_size=64,
            batch_first=True,
            dropout=0.3,
            bidirectional=True
        )

        # Dropout and classifier
        self.dropout = nn.Dropout(0.5)
        self.relu = nn.ReLU()
        
        # Classifier (128 = 64*2 for bidirectional)
        self.fc1 = nn.Linear(128, 64)
        self.fc2 = nn.Linear(64, num_classes)
        
        # Add layer normalization for stability
        self.layer_norm = nn.LayerNorm(256)

    def forward(self, x):
        # 1. CNN feature extraction
        x = self.cnn(x)  # Output: (batch, 256, 8)
        
        # 2. Reshape for LSTM: (batch, time, channels)
        x = x.permute(0, 2, 1)  # (batch, 8, 256)
        
        # 3. Layer normalization
        x = self.layer_norm(x)
        
        # 4. First LSTM layer
        x, _ = self.lstm1(x)
        x = self.dropout(x)
        
        # 5. Second LSTM layer
        x, _ = self.lstm2(x)
        x = self.dropout(x)
        
        # 6. Take the last time step
        last_time_step = x[:, -1, :]
        
        # 7. Classifier
        x = self.relu(self.fc1(last_time_step))
        x = self.dropout(x)
        output = self.fc2(x)
        
        return output