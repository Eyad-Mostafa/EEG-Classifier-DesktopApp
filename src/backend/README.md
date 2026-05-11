# EEG-Classifier


## Setup

1. Clone the repository
2. Create virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
4. Copy `.env.example` to `.env`:
   ```bash
   copy .env.example .env
   ```
5. Run the application:
   ```bash
   uvicorn app.main:app --reload
   ```

## API Documentation

Visit http://localhost:8000/docs for interactive API documentation.
