# 📸 Google Drive to Lightroom CC Sync Tool

Automatically sync and upload all files from a Google Drive folder into a selected Adobe Lightroom CC album.

This open-source tool is designed for photographers and content creators who want a fast, reliable way to back up or organize images stored in Google Drive directly into Lightroom without manual uploads.

---

## ✨ Features

- 🔁 Automatically uploads all files from a specified Google Drive folder to a Lightroom CC album
- 🔒 OAuth-based secure authentication for Google and Adobe APIs
- 🛠 CLI-based prompts for easy folder and album selection
- 🚫 Lightroom API does **not** detect duplicates — files may be re-uploaded  

---

## ⚙️ Prerequisites

- Python 3.8 or later  
- A Google Cloud project with Drive API enabled  
- An Adobe Developer account with Lightroom API access  
- `pip`, `virtualenv`, and a basic understanding of Python  

---

## 🚀 Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/ekaratzaferis/drive-to-lightroomcc.git
cd drive-to-lightroomcc
```

### 2. Set Up Virtual Environment

```bash
python -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Google Drive API

* Go to [Google Cloud Console](https://console.cloud.google.com/)
* Create a project and enable the **Google Drive API**
* Generate OAuth 2.0 credentials (Client ID)
* Download the credentials file
* Rename it to `google_credentials.json` and place it in the root directory of the project

### 5. Configure Adobe Lightroom API

* Visit [Adobe Developer Console](https://developer.adobe.com/console/)
* Create a new project and add the **Lightroom API**
* Set up OAuth credentials and permissions as instructed
* Save any credentials or secrets as required

---

## ▶️ Usage

### First-Time Setup (Authentication)

```bash
python main.py
```

* Follow the authentication prompts for both Google and Adobe

### Start Sync

```bash
python main.py
```

* Select a Google Drive folder
* Choose a Lightroom CC album
* Files will begin uploading

> ⚠️ **Note:** Lightroom API does not check for duplicates. If files were already uploaded before, they will be uploaded again.

---

## 🧪 Development

### Install New Packages

```bash
pip install <package-name>
pip freeze > requirements.txt
```

### Deactivate the Virtual Environment

```bash
deactivate
```

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repo
2. Create a new branch
3. Make your changes
4. Open a pull request

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).

---
