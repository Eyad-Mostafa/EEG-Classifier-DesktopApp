import io
import numpy as np
import pandas as pd

class EEGGeneratorService:
    @staticmethod
    def generate_synthetic_csv(
        duration: int = 4, 
        fs: int = 250, 
        subjects: list = None
    ) -> io.StringIO:
        """
        Generates synthetic EEG data using vectorized NumPy operations.
        """
        if subjects is None:
            subjects = ['1', '2', '3', '4', '5']
        
        sessions = [1, 2, 3]
        trials = [1, 2, 3, 4, 5]
        num_points = fs * duration
        rows = []

        # Pre-calculate time array
        t = np.linspace(0, duration, num_points)

        for subject in subjects:
            for session in sessions:
                for trial in trials:
                    # Logic: 0 for odd trials (Alpha 10Hz), 1 for even (Beta 25Hz)
                    label = 0 if trial % 2 != 0 else 1
                    freq = 10 if label == 0 else 25

                    # Vectorized Signal Generation (16 channels at once)
                    base_signal = 0.001 * np.sin(2 * np.pi * freq * t)
                    noise = 0.0001 * np.random.randn(16, num_points)
                    trial_signals = base_signal + noise

                    # Construct rows
                    for time_idx in range(num_points):
                        row = {
                            'subject_id': subject,
                            'session_id': session,
                            'trial_id': trial,
                            'labels': label,
                            'category': 'Imagery',
                            'time_index': time_idx,
                        }
                        for ch_idx in range(16):
                            row[f'channel_{ch_idx + 1}'] = trial_signals[ch_idx, time_idx]
                        rows.append(row)

        df = pd.DataFrame(rows)
        stream = io.StringIO()
        df.to_csv(stream, index=False)
        stream.seek(0)
        return stream