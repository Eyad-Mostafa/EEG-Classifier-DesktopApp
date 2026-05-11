import torch
import torch.nn as nn

class CNN_LSTM_MEAN_1(nn.Module):
    def __init__(self, num_channels=16, num_classes=4):
        super(CNN_LSTM_MEAN_1, self).__init__()

        # 1. CNN Block
        self.cnn = nn.Sequential(
            nn.Conv1d(in_channels=num_channels, out_channels=32, kernel_size=32, stride=2, padding=15),
            nn.BatchNorm1d(32),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=3, stride=2),

            nn.Conv1d(in_channels=32, out_channels=64, kernel_size=3, padding=0),
            nn.BatchNorm1d(64),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=3, stride=2),

            nn.Conv1d(in_channels=64, out_channels=128, kernel_size=3, padding=0),
            nn.BatchNorm1d(128),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=3, stride=2),

            nn.Conv1d(in_channels=128, out_channels=256, kernel_size=3, padding=0),
            nn.BatchNorm1d(256),
            nn.ReLU(),
            nn.MaxPool1d(kernel_size=3, stride=2)
        )

        # 2. LSTM Block
        self.lstm1 = nn.LSTM(input_size=256, hidden_size=64, batch_first=True)
        self.lstm2 = nn.LSTM(input_size=64, hidden_size=32, batch_first=True)

        self.dropout = nn.Dropout(0.5)
        self.relu = nn.ReLU()

        # 3. Classifier Block
        self.fc = nn.Linear(32, num_classes)

    def forward(self, x):
        x = self.cnn(x)
        x = x.permute(0, 2, 1) # Reshape for LSTM (Batch, Seq_len, Features)

        x, (h_n, c_n) = self.lstm1(x)
        x = self.relu(x)
        x = self.dropout(x)

        x, (h_n, c_n) = self.lstm2(x)
        x = self.relu(x)
        x = self.dropout(x)

        # last_time_step = x[:, -1, :]
        # output = self.fc(last_time_step)

        x = torch.mean(x, dim=1)
        output = self.fc(x)

        return output