# K-Panel: Multi-Agent AI Workshop — Nasscom Future Forge 2026

Welcome to the **K-Panel** hands-on multi-agent workshop! This repository serves as the official interactive environment and code foundation for our multi-agent workshop session at **Nasscom Future Forge 2026**.

---

## 📅 Event & Session Overview

- **Event**: [Nasscom Future Forge 2026](https://lnkd.in/daZE65BH) (`#NasscomFutureForge2026`)
- **Dates**: August 6th & 7th, 2026
- **Venue**: Taj Yeshwantpur, Bengaluru
- **Registration**: [Register Now](https://lnkd.in/daZE65BH)
- **Theme**: Deeptech at Scale — Spanning identity infrastructure, autonomous robotics, applied AI, and cybersecurity to answer how India builds enterprise-ready systems that hold up at scale.

### 🎙️ Workshop Panel & Facilitators
- **Aditi Sharma Goyal**
- **Srivatsan Sundaravaradan**
- **Kaushal Srivastava**
- **Goutham Kumar**
- **Vishnu RNS**
- **Shashank Sharma**

---

## 💡 What is K-Panel?

**K-Panel** is a lightweight, hand-rolled **multi-agent orchestration framework** designed specifically as a teaching tool. It reveals the exact mechanics that production frameworks (such as LangGraph, CrewAI, AutoGen, or OpenAI Swarm) abstract away:

1. **Agent Personas Registry**: Declarative YAML configuration files (`agents/*.yaml`) defining expert system prompts, roles, and metadata with runtime hot-reloading.
2. **Model Client & Observability**: Thin HTTP wrapper around OpenAI-compatible APIs (`/v1/chat/completions`) with real-time terminal tracing (`print_llm_log`).
3. **Stateless Orchestration Loop**: Round-robin turn taking (`/orchestrate`) across selected agents, culminating in automated PRD (Product Requirements Document) synthesis.
4. **Single-Agent 1-on-1 Chat**: Direct interaction with specific agent personas with Server-Sent Events (SSE) streaming (`/chat`).
5. **Downstream Pipeline Synthesis**: Transforming multi-agent discussion PRDs into fully functional, self-contained single-page web prototypes streamed live (`/visualize/stream`).

---

## 🚀 Quick Start for Workshop Participants

### Prerequisites
- **Python 3.9+** installed
- Internet access (for LLM API calls and CDN resources)
- An OpenAI-compatible API key (Groq, OpenRouter, Gemini, OpenAI, or local Ollama).  
  📘 **See the full [LLM_GUIDE.md](LLM_GUIDE.md) for direct key links and setup guides.**

#### 🔑 LLM Provider Quick Setup Summary

| Provider | Direct Key Link | Base URL | Recommended Model Name |
| :--- | :--- | :--- | :--- |
| **⚡ GroqCloud** | [console.groq.com/keys](https://console.groq.com/keys) | `https://api.groq.com/openai/v1` | `llama-3.3-70b-versatile` |
| **🌐 OpenRouter** | [openrouter.ai/keys](https://openrouter.ai/keys) | `https://openrouter.ai/api/v1` | `openai/gpt-4o-mini` |
| **✨ Google Gemini** | [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) | `https://generativelanguage.googleapis.com/v1beta/openai` | `gemini-2.5-pro` |
| **🟢 OpenAI** | [platform.openai.com/api-keys](https://platform.openai.com/api-keys) | `https://api.openai.com/v1` | `gpt-4o-mini` |

### Step 1: Clone the Repository
Workshop Short Link: **https://tinyurl.com/netappnasscom**  
*(Alternative: `https://tinyurl.com/nasscom-kpanel`)*

```bash
git clone https://tinyurl.com/netappnasscom
# Or using full URL:
# git clone https://github.com/GouthamKumar-R/multi-agent-k-panel.git
cd multi-agent-k-panel
```

### Step 2: Extract & Launch for Your OS

The repository includes a launcher script for every major platform that sets up a Python virtual environment, installs dependencies (`requirements.txt`), and launches both the backend and frontend:

- **Windows**:
  ```cmd
  start-in-windows.bat
  ```
- **macOS**:
  ```bash
  chmod +x start-in-mac.sh
  ./start-in-mac.sh
  ```
- **Linux**:
  ```bash
  chmod +x start-in-linux.sh
  ./start-in-linux.sh
  ```

### Step 3: Access the Application
Once launched:
- **Backend API**: `http://127.0.0.1:8877`
- **Frontend UI**: `http://127.0.0.1:8080/k-panel.html` (opens automatically in your browser)

---

## 🛠️ Workshop Hands-On Activities

During this workshop, participants will progress through three main exercises:

### Activity 1: Run a Multi-Agent Panel Discussion
1. Open `http://127.0.0.1:8080/k-panel.html`.
2. Configure your **API Base URL**, **Model Name**, and **API Key** in the settings drawer.
3. Select 3-4 agent experts (e.g. Brand Manager, Copywriter, Graphic Designer, Marketing Analyst).
4. Enter a discussion topic (e.g., *"Building an Enterprise AI Security Gateway for Autonomous Robotics"*).
5. Step through the discussion turn-by-turn to watch the agents debate and contribute.
6. Observe how the final turn automatically synthesizes the discussion into a Markdown PRD.

### Activity 2: Create Custom Deeptech Agents
1. Click **+ Add Agent** in the UI (or create a new `.yaml` file under `agents/`).
2. Add custom Deeptech roles relevant to Nasscom Future Forge:
   - **Identity Infrastructure Lead**
   - **Autonomous Robotics Architect**
   - **AI Safety & Cybersecurity Specialist**
3. Save the agent — K-Panel automatically hot-reloads the persona into memory without requiring a server restart.

### Activity 3: Generate Live Prototype Artifacts
1. After completing a panel discussion, click **Visualize Web Prototype**.
2. Watch the downstream synthesis pipeline stream live HTML/CSS code.
3. Inspect the live interactive prototype generated directly from the panel's consensus.

---

## 📁 Repository Structure

```text
multi-agent-k-panel/
├── agents/                                 # Declarative YAML Agent Personas
│   ├── brand_manager.yaml
│   ├── content_creator.yaml
│   ├── copywriter.yaml
│   ├── creative_director.yaml
│   ├── digital_marketing_manager.yaml
│   ├── graphic_designer.yaml
│   ├── influencer_marketing_specialist.yaml
│   ├── marketing_analyst.yaml
│   ├── social_media_manager.yaml
│   └── video_producer_editor.yaml
├── k-panel.py                              # FastAPI Backend (Orchestrator & Model Client)
├── k-panel.html                            # Glassmorphism Frontend Web UI
├── requirements.txt                        # Python dependencies (fastapi, uvicorn, requests, httpx, pyyaml)
├── starting_guide.md                       # Quick launcher reference guide
├── start-in-windows.bat                    # Windows automatic setup script
├── start-in-mac.sh                         # macOS automatic setup script
├── start-in-linux.sh                       # Linux automatic setup script
├── LLM_GUIDE.md                            # Comprehensive LLM Key & Provider Guide
└── README.md                               # Workshop & Repository Guide
```

---

## ⚡ Backend API Endpoints Reference

| Endpoint | Method | Description |
| :--- | :--- | :--- |
| `/agents` | `GET` | Lists summary of all registered agents |
| `/agents/{id}` | `GET` | Fetches full agent YAML spec & system prompt |
| `/agents` | `POST` | Dynamically registers and saves a new agent YAML |
| `/orchestrate` | `POST` | Advances panel discussion by 1 turn / generates PRD |
| `/chat` | `POST` | 1-on-1 agent conversation (supports `?stream=1`) |
| `/visualize/stream` | `POST` | Streams single-page HTML website prototype based on PRD |

---

## 🤝 Need Help During the Workshop?

Reach out to any of the session panel members or facilitators (**Aditi Sharma Goyal, Srivatsan Sundaravaradan, Kaushal Srivastava, Goutham Kumar, Vishnu RNS, Shashank Sharma**) during the live session at Taj Yeshwantpur!

Happy **Learning at #NasscomFutureForge2026**! 🎉
