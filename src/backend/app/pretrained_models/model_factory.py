from app.pretrained_models.model1 import CNN_LSTM_MEAN_1
from app.pretrained_models.model2 import CNN_LSTM

from app.pretrained_models.eegnet import EEGNet

# Map the string from your JSON file to the actual PyTorch class
ARCHITECTURE_MAP = {
    "CNN-LSTM_MEAN_1": CNN_LSTM_MEAN_1,
    "CNN_LSTM": CNN_LSTM,
    "EEGNet": EEGNet
}

def get_model_class(architecture_name: str):
    if architecture_name not in ARCHITECTURE_MAP:
        raise ValueError(f"Architecture '{architecture_name}' is not registered in the Model Factory.")
    return ARCHITECTURE_MAP[architecture_name]