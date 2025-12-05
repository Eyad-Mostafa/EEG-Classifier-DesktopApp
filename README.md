<div align="center">

  <img src="./icon.png" alt="EEG Classifier Logo" width="120" height="120" />

  # EEG Classifier

  **A Professional Desktop Suite for Offline EEG Signal Analysis**

  [![Platform](https://img.shields.io/badge/platform-win%20%7C%20mac%20%7C%20linux-lightgrey?style=flat-square)](https://github.com/Eyad-Mostafa/EEG-Classifier-DesktopApp/releases)
  [![Version](https://img.shields.io/github/v/release/Eyad-Mostafa/EEG-Classifier-DesktopApp?style=flat-square&color=3b82f6&label=version)](https://github.com/Eyad-Mostafa/EEG-Classifier-DesktopApp/releases/latest)
  
  <p align="center">
    <a href="#-algorithm-suite">Algorithms</a> •
    <a href="#-tech-stack">Tech Stack</a> •
    <a href="#-download--installation">Download</a> •
    <a href="#the-team">The Team</a>
  </p>
</div>

---

## 📖 Overview

**EEG Classifier** is a robust, cross-platform desktop application designed for the preprocessing, analysis, and visualization of Electroencephalography (EEG) data. 

Unlike web-based tools, this application runs entirely **offline**, ensuring strict data privacy and leveraging the full performance of your local machine for complex signal processing algorithms. It bridges the gap between modern UI design and powerful scientific computing.

## 🚀 Algorithm Suite

We have implemented a robust library of signal processing techniques powered by a **specialized Python analysis backend**. The suite is designed to handle the complete analysis lifecycle:

* **Advanced Preprocessing:** A complete pipeline for signal conditioning, automated artifact removal, and adaptive filtering.
* **Spectral Analysis:** Tools for investigating frequency dynamics, including Power Spectral Density (PSD) and Time-Frequency distributions.
* **Feature Extraction:** Specialized metrics for deep analysis, such as Differential Entropy and Connectivity mapping.

---

## 🛠 Tech Stack

This project utilizes a **Hybrid Architecture** to combine the best of web technologies with scientific Python computing.

| Component | Technology | Description |
| :--- | :--- | :--- |
| **Frontend** | ![Angular](https://img.shields.io/badge/-Angular-dd0031?style=flat-square&logo=angular&logoColor=white) | UI/UX, State Management, Visualization |
| **Backend** | ![Python](https://img.shields.io/badge/-Python-3776AB?style=flat-square&logo=python&logoColor=white) | FastAPI engine for Signal Processing (Scipy, MNE, Sklearn) |
| **Wrapper** | ![Electron](https://img.shields.io/badge/-Electron-47848F?style=flat-square&logo=electron&logoColor=white) | Desktop integration and process orchestration |
| **CI/CD** | ![GitHub Actions](https://img.shields.io/badge/-GitHub_Actions-2088FF?style=flat-square&logo=github-actions&logoColor=white) | Automated multi-OS build and release pipeline |

---

## 📥 Download & Installation

We provide standalone installers for all major operating systems. No Python or Node.js installation is required.

### [👉 Download Latest Release](https://github.com/Eyad-Mostafa/EEG-Classifier-DesktopApp/releases/latest)

### Windows
1. Download the file ending in `.Setup.exe`.
2. Run the installer.
3. **Security Warning:** Since this is a university project, it is not digitally signed by Microsoft. 
   * If you see *"Windows protected your PC"*:
   * Click **More info** → Click **Run anyway**.

### macOS
1. Download the `.dmg` file.
2. Drag the app to your Applications folder.
3. **Security Warning:** If you see *"App cannot be opened because the developer cannot be verified"*:
   * Right-Click the app icon → Select **Open** → Click **Open Anyway**.

### Linux
1. Download the `.AppImage` file.
2. Right-click the file > Properties > Permissions > **Allow executing file as program**.
3. Double-click to run.

---

<div id="the-team"></div>

## 🧑‍💻 The Team

This project was developed as a graduation project for the 2025/2026 academic year.

| Name | GitHub |
| :--- | :--- |
| **Eyad Mostafa** | [@Eyad-Mostafa](https://github.com/Eyad-Mostafa) |
| **Abobaker Mohamed** | [@abobakerer](https://github.com/abobakerer) |
| **Mennatullah Ahmed** | [@Menna-Allah-A](https://github.com/Menna-Allah-A) |
| **Omar Nasser** | [@omarnasser10](https://github.com/omarnasser10) |

<br>

**Under the supervision of:**
### Prof. [Mohamed Fakhry](https://github.com/m-fakhry)

---

<div align="center">
  <sub>Built with ❤️ by the EEG Project Team • © 2025</sub>
</div>
