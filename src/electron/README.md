# EEG Classifier - Electron Desktop App

This repository contains the Electron wrapper for the EEG Classifier application. To run or package this desktop app, you must first compile the Angular frontend and the Python FastAPI backend, and place them into the correct directories here.

## 📁 Required Folder Structure
Before running or packaging the Electron app, your directory must look like this:

```text
graduation-project-electron/
│
├── backend-bin/
│   └── backend/                 <-- Python compiled binary folder goes here
│
├── dist/
│   └── eeg-classifier-angular/  <-- Angular compiled UI goes here
│
├── electron/                    <-- Electron main process scripts
├── package.json
└── ...

```

---

## 🛠️ Step 1: Build the Frontend (Angular)

1. Open your terminal and navigate to your **Angular frontend repository**.
2. Run the build command:
```bash
ng build --configuration production --base-href ./

```


3. Copy the generated `eeg-classifier-angular` folder (located inside the `dist` folder of your Angular repo).
4. Paste it into the `dist` folder of **this Electron repository** so the path becomes: `dist/eeg-classifier-angular/`.

---

## 🐍 Step 2: Build the Backend (Python)

1. Open your terminal and navigate to your **Python backend repository**.
2. Ensure your virtual environment is activated and all requirements are installed.
3. Run the following exact `pyinstaller` command to compile the backend:
```bash
pyinstaller --noconfirm --windowed --name backend --add-data "app;app" --add-data "alembic;alembic" --add-data "alembic.ini;." --hidden-import=scipy.signal --hidden-import=sklearn --hidden-import=sklearn.decomposition --hidden-import=sklearn.utils --hidden-import=pandas --hidden-import=seaborn --hidden-import=networkx --hidden-import=numpy --hidden-import=sqlalchemy --hidden-import=sqlite3 --hidden-import=platformdirs --hidden-import=pycrostates --collect-all mne --collect-all torch --copy-metadata torch --copy-metadata pycrostates app/main.py

```


4. Copy the generated `backend` folder (located inside the `dist` folder of your Python repo).
5. Paste it into the `backend-bin` folder of **this Electron repository** so the path becomes: `backend-bin/backend/`.

---

## 🚀 Step 3: Run the Application (Development)

Once the frontend and backend are placed in their respective folders, you can run the app locally.

1. Install the Electron dependencies:
```bash
npm install

```


2. Start the application:
```bash
npm start

```



---

## 📦 Step 4: Package the Application (Production)

To create standalone, installable executables (e.g., `.exe` for Windows) containing the UI and the Python engine, use the following commands.

**For Windows (.exe):**

```bash
npm run package

```

**For macOS (.dmg):**
*(Requires running on a Mac)*

```bash
npx electron-builder build --mac --x64

```

**For Linux (.AppImage):**
*(Requires running on Linux)*

```bash
npx electron-builder build --linux --x64

```

The final executable files will be generated inside the `release/` folder.
