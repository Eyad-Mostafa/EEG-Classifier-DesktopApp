# 🧠 EEG Classifier

A modern web application for uploading and analyzing EEG (Electroencephalography) data.
Currently in the design and integration phase, this frontend is built to communicate with a RESTful backend API for EEG preprocessing, feature extraction, and classification.

---

## 🚀 How to Run This Angular Project

### 1️⃣ Install Node.js

After installation, verify Node.js and npm:

```bash
node -v
npm -v
```

---

### 2️⃣ Install Angular CLI

Install Angular globally:

```bash
npm install -g @angular/cli
```

Check the installation:

```bash
ng version
```

---

### 3️⃣ Clone the Project

```bash
git clone https://github.com/Eyad-Mostafa/eeg-classifier-frontend.git
cd eeg-classifier-frontend
```

---

### 4️⃣ Install Dependencies

```bash
npm install
```

---

### 5️⃣ Run the Development Server

```bash
ng serve
```

Then open your browser at:
👉 **[http://localhost:4200/](http://localhost:4200/)**

---

## ⚙️ Environment Configuration

Edit your environment file at:

```
src/environments/environment.ts
```

Default configuration:

```ts
export const environment = {
  production: false,
  apiUrl: 'http://localhost:8000/api',
  maxFileSize: 100 * 1024 * 1024, // 100MB
  allowedFileTypes: ['.csv'],
  defaultSamplingRate: 256,
  defaultChannels: 64
};
```

* **apiUrl** → Backend API base URL
* **maxFileSize** → Upload limit
* **allowedFileTypes** → Currently `.csv` only
* **defaultSamplingRate** and **defaultChannels** → Default EEG parameters

---

## 🧠 Current Features

* Upload EEG data (`.csv` format)
* Drag-and-drop upload with progress simulation
* Workflow navigation (Upload → Configuration)
* File preview with validation (size, type, etc.)
* Configurable parameters from environment settings
* backend API integration for real uploads
* Preprocessing and feature extraction configuration

---

## 🔮 Planned Additions

* EEG classification and result visualization
* Algorithm information panel (FFT, Band-pass, etc.)

---

## 🧰 Technologies Used

* Angular 17
* TypeScript
* RxJS
* HTML5 / CSS3

---

## 📄 License

MIT License
