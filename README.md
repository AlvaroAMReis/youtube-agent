# 🏛️ YouTube Autonomous Agent v2.0

> Automatically creates and publishes Stoicism videos + Shorts to YouTube using AI.

![Python](https://img.shields.io/badge/Python-3.10+-blue)
![GPT-4o](https://img.shields.io/badge/OpenAI-GPT--4o-green)
![ElevenLabs](https://img.shields.io/badge/ElevenLabs-TTS-orange)
![YouTube API](https://img.shields.io/badge/YouTube-Data%20API%20v3-red)

---

## 📖 Overview

This agent autonomously runs a faceless YouTube channel about Stoic philosophy. Every execution generates a complete video from scratch — script, narration, visuals, editing, and upload — with zero manual intervention.

**Live channel:** [The Silent Sage](https://www.youtube.com/@TheSilentSage-c4j)

---

## ✨ Features

- 🤖 **AI Script Generation** — GPT-4o writes unique Stoicism scripts every run
- 🎙️ **Text-to-Speech** — ElevenLabs generates natural narration
- 🎬 **Auto Video Editing** — MoviePy assembles clips with background videos from Pexels
- 🖼️ **AI Thumbnails** — DALL-E 3 generates custom thumbnails
- 📱 **YouTube Shorts** — Automatically creates a vertical Short from the best scene
- 📤 **Auto Upload** — Publishes to YouTube with title, description, tags and thumbnail
- ⏰ **Scheduled** — Runs automatically via Windows Task Scheduler

---

## 🏗️ Architecture

```
youtube-agent/
├── main.py                  # Full agent (long video + Short)
├── main_shorts.py           # Shorts-only agent (cheaper)
├── modules/
│   ├── script_generator.py  # Module 1: GPT-4o script generation
│   ├── voice_generator.py   # Module 2: ElevenLabs TTS
│   ├── media_generator.py   # Module 3: Pexels + DALL-E 3
│   ├── video_editor.py      # Module 4: MoviePy/FFmpeg editing
│   ├── youtube_uploader.py  # Module 5: YouTube Data API v3
│   └── shorts_generator.py  # Module 6: Shorts creation & upload
├── logs/                    # Execution logs + JSON reports
├── .env.example             # Environment variables template
└── requirements.txt         # Python dependencies
```

---

## 🔄 Workflow

```
GPT-4o          ElevenLabs       Pexels + DALL-E    MoviePy         YouTube API
   │                │                  │               │                │
   ▼                ▼                  ▼               ▼                ▼
Generate       Narrate the        Download BG      Edit final       Upload video
 script  ───►  script to  ───►   videos + gen ──► video 16:9  ───► + thumbnail
               MP3 audio         thumbnail        + Short 9:16     + Short
```

---

## 💰 Cost per Run

| Service | Long Video | Short Only |
|---|---|---|
| OpenAI GPT-4o | ~$0.15 | ~$0.05 |
| DALL-E 3 | ~$0.04 | — |
| ElevenLabs | ~$0.95 | ~$0.20 |
| Pexels | Free | Free |
| **Total** | **~$1.20** | **~$0.25** |

**Monthly cost (4x/week):** ~$15/month

---

## ⚙️ Setup

### 1. Clone the repository
```bash
git clone https://github.com/yourusername/youtube-agent.git
cd youtube-agent
```

### 2. Create virtual environment
```bash
python -m venv venv
venv\Scripts\activate  # Windows
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
pip install "Pillow==9.5.0"
pip install "moviepy==1.0.3"
```

### 4. Configure environment variables
```bash
cp .env.example .env
# Edit .env with your API keys
```

### 5. Setup YouTube OAuth2
- Go to [Google Cloud Console](https://console.cloud.google.com)
- Enable YouTube Data API v3
- Create OAuth2 Desktop credentials
- Download `client_secrets.json` to project root

### 6. Install ImageMagick (Windows)
Download from [imagemagick.org](https://imagemagick.org/script/download.php#windows) and install with:
- ✅ Add application directory to system path
- ✅ Install legacy utilities

---

## 🔑 Environment Variables

Create a `.env` file based on `.env.example`:

```env
OPENAI_API_KEY=your_openai_key
ELEVENLABS_API_KEY=your_elevenlabs_key
ELEVENLABS_VOICE_ID=your_voice_id
PEXELS_API_KEY=your_pexels_key
YOUTUBE_CLIENT_SECRETS_FILE=client_secrets.json
CHANNEL_NICHE=Stoicism
SCRIPT_LANGUAGE=en
CREATE_SHORT=true
```

---

## 🚀 Usage

### Full video + Short
```bash
python main.py
```

### Short only (cheaper)
```bash
python main_shorts.py
```

---

## ⏰ Automation (Windows Task Scheduler)

| Day | Time | Script | Cost |
|---|---|---|---|
| Monday | 14:00 | main.py | ~$1.20 |
| Thursday | 14:00 | main.py | ~$1.20 |
| Tuesday | 12:00 | main_shorts.py | ~$0.25 |
| Friday | 12:00 | main_shorts.py | ~$0.25 |

---

## 📦 Requirements

```
openai>=1.30.0
elevenlabs>=1.0.0
requests>=2.31.0
moviepy==1.0.3
Pillow==9.5.0
numpy>=1.24.0
google-api-python-client>=2.100.0
google-auth-httplib2>=0.1.1
google-auth-oauthlib>=1.1.0
python-dotenv>=1.0.0
```

---

## ⚠️ Important Notes

- Never commit `.env`, `token.json`, or `client_secrets.json`
- ElevenLabs Starter plan: 30,000 credits/month (~12 full runs)
- YouTube has a daily upload limit for new channels
- First run will open browser for YouTube OAuth2 authorization

---

## 📊 Channel Growth Projection

| Month | Videos | Shorts | Subscribers |
|---|---|---|---|
| 1 | 8 | 12 | 10-50 |
| 3 | 24 | 36 | 200-500 |
| 6 | 48 | 72 | 1k-3k |
| 12 | 96 | 144 | 5k-15k |

---

## 📄 License

MIT License — free to use and modify.

---

*Built with ❤️ for The Silent Sage channel*