# CollegeDB Engine

CollegeDB Engine is a high-performance, asynchronous Web Application designed to automatically extract data, find official websites, and scrape high-quality transparent logos for any list of colleges.

Built with a fast **Python FastAPI** backend and a gorgeous **Tailwind CSS v4** frontend, CollegeDB turns hours of manual data entry into a simple drag-and-drop experience.

## ✨ Features

- **Drag-and-Drop Interface**: Upload your raw `colleges.csv` file directly from the browser.
- **Live Terminal Output**: Watch the Python scraper work in real-time via Server-Sent Events (SSE) streaming logs straight to your UI.
- **Wikidata Integration**: Automatically resolves college names to their Wikidata entities to extract locations (City/State) and historical rankings.
- **Logo Scraping Engine**: Automatically searches and extracts official transparent logos from university websites and GitHub repositories.
- **Automated Zipping**: Packages your enriched dataset (`colleges.csv`, `engineering_colleges.csv`) and your `logos/` directory into a single `Dataset_Results.zip` file for easy download.

## 🚀 Quick Start (Local Deployment)

### Prerequisites
Make sure you have Python 3.9+ installed on your machine.

### Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/trghcj/CollegeDB.git
   cd CollegeDB
   ```

2. Install the required dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the App

1. Start the FastAPI ASGI server:
   ```bash
   uvicorn app:app --reload
   ```
2. Open your browser and navigate to `http://127.0.0.1:8000`.

## ☁️ Cloud Deployment (Render, Heroku, etc.)

This application is fully compatible with PaaS providers like Render.com.

1. Connect your GitHub repository to a new Web Service.
2. Set the Build Command:
   ```bash
   pip install -r requirements.txt
   ```
3. Set the Start Command:
   ```bash
   python -m uvicorn app:app --host 0.0.0.0 --port $PORT
   ```

*Note: The Start Command must use `python -m uvicorn` on some cloud providers to ensure the module is found in the system path.*

## 📂 Project Structure

```
CollegeDB/
├── app.py                     # FastAPI Backend Server & SSE routing
├── build_dataset.py           # Core execution script for the data pipeline
├── requirements.txt           # Python dependencies
├── static/                    # Frontend Assets
│   ├── index.html             # Main Tailwind v4 UI
│   ├── script.js              # SSE Client logic & UI state
│   └── logo.png               # Official CollegeDB Branding
└── scraper/                   # Core Scraping Logic
    ├── website_search.py      # DDGS image searching & URL resolution
    └── ...
```

## 📝 Usage

1. Create a CSV file with at least one column named `college_name`.
2. Drag and drop the CSV into the CollegeDB Web UI.
3. Wait for the live terminal to display `--- PIPELINE COMPLETE ---`.
4. Click the vibrant green **Download Dataset (.zip)** button.
