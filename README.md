# YTForge

YTForge is a powerful web-based interface for `yt-dlp`, allowing you to easily download videos, extract audio, and manage downloads from various platforms.

## Features

- **Video Downloads**: Download videos in various formats and resolutions.
- **Audio Extraction**: Extract high-quality audio in multiple formats (MP3, etc.).
- **Metadata Retrieval**: View video information, thumbnails, and subtitles.
- **Modern UI**: Clean and responsive React-based frontend.

## Setup & Running

### Prerequisites

- Python 3.8+
- Node.js & npm
- FFmpeg (for video/audio processing)

### Quick Start

1. **Install Backend Dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Install Frontend Dependencies**:
   ```bash
   cd frontend
   npm install
   ```

3. **Run the Application**:
   - Start the backend:
     ```bash
     python files/app.py
     ```
   - Start the frontend:
     ```bash
     cd frontend
     npm run dev
     ```

## Project Architecture & Structure

```mermaid
graph TD
    subgraph Client_Side [Frontend - React/Vite]
        UI[User Interface]
        Req[API Request Handler]
        UI --> Req
    end

    subgraph Server_Side [Backend - Flask]
        API[Flask API Routes]
        JobQ[Job Manager / Threading]
        YTDLP[yt-dlp Integration]
        
        Req -->|POST /api/info| API
        Req -->|POST /api/download| API
        API --> JobQ
        JobQ --> YTDLP
    end

    subgraph External [External Tools]
        YouTube[(YouTube / Others)]
        FFMPEG[FFmpeg]
        
        YTDLP -->|Fetch Info/Stream| YouTube
        YTDLP -->|Post-process| FFMPEG
    end

    subgraph Storage [Local Storage]
        DL_DIR[(downloads/ directory)]
        YTDLP -->|Save File| DL_DIR
        DL_DIR -->|Serve File| API
    end

    API -->|Response / Status| UI
```

### Folder Layout

```text
YTForge/
├── files/
│   ├── app.py          # Flask Backend logic & API
│   └── run.sh          # Automation script
├── frontend/           # React Frontend (Vite)
│   ├── src/            # Components & Logic
│   └── public/         # Assets
├── downloads/          # Temporary video/audio storage
├── requirements.txt    # Python dependencies
└── README.md           # Documentation
```
