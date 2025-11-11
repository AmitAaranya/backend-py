# Farmer-APP Backend (Python)

## Technologies Used
1. FastAPI (Python)
2. Google Firestore (NoSQL Database)

## Prerequisites
1. Python 3.9 or higher
2. pip (Python package manager)
3. Git (for cloning the repository)
4. Google Cloud credentials (stored in `data/google_cred.json`)
5. Docker (optional, for containerized deployment)

## How to Install Locally (Windows)

1. **Clone the repository:**
   ```powershell
   git clone https://github.com/AmitAaranya/backend-py.git
   cd backend-py
   ```

2. **Set up a virtual environment:**
   ```powershell
   python -m venv venv
   .\venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```
4. **Create a `.env` file in the root directory:**
   Create a new file named `.env` in the root of the project (same level as `run.py`).

5. **Add environment variables:**
   Add your environment-specific variables in the following format:
   ```env
   GOOGLE_APPLICATION_CREDENTIALS=data/google_cred.json
   DATABASE_URL=your_database_url_here
   SECRET_KEY=your_secret_key_here
   ```

6. **Run the application:**
   ```powershell
   python .\run.py
   ```

7. **Access the application:**
   Open your browser and navigate to `http://127.0.0.1:8080`.


## Notes
- Ensure that the `data/google_cred.json` file contains valid Google Cloud credentials for Firestore.
- For Docker users, you can build and run the application using the provided `Dockerfile`.
