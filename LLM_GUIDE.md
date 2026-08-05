# 🔑 K-Panel LLM Configuration & API Key Guide

This guide provides step-by-step instructions for getting API keys, setting up Base URLs, and choosing the best model names for **K-Panel**.

---

## ⚡ 1. GroqCloud (Ultra-Fast & Free Tier)

Groq offers ultra-low latency inference with generous free-tier quotas.

- **🔑 Direct Key Link**: [https://console.groq.com/keys](https://console.groq.com/keys)
- **How to Get Your Key**:
  1. Go to [https://console.groq.com/keys](https://console.groq.com/keys) and sign in.
  2. Click **Create API Key**.
  3. Name your key and copy the generated secret string (starts with `gsk_`).
- **🌐 Base URL**: `https://api.groq.com/openai/v1`
- **🎯 Recommended Models**:
  - **`llama-3.3-70b-versatile`** *(Recommended: Best for HTML prototypes & PRD synthesis)*
  - **`mixtral-8x7b-32768`**
  - **`llama-3.1-8b-instant`** *(Fastest for turn-by-turn agent discussions)*

---

## 🌐 2. OpenRouter (Access 100+ Models with 1 Key)

OpenRouter aggregates models from OpenAI, Anthropic, Meta, Google, and open-source providers under a single OpenAI-compatible endpoint.

- **🔑 Direct Key Link**: [https://openrouter.ai/keys](https://openrouter.ai/keys)
- **How to Get Your Key**:
  1. Log in at [https://openrouter.ai/keys](https://openrouter.ai/keys) using Google or GitHub.
  2. Click **Create Key**.
  3. Copy your key (starts with `sk-or-v1-`).
- **🌐 Base URL**: `https://openrouter.ai/api/v1`
- **🎯 Recommended Models**:
  - **`openai/gpt-4o-mini`** *(Verified & recommended: Fast, high quality, and affordable)*
  - **`meta-llama/llama-3.3-70b-instruct`**
  - **`google/gemini-2.0-flash-lite-001:free`**

---

## ✨ 3. Google Gemini (Google AI Studio)

Google AI Studio provides an official OpenAI-compatible endpoint for native Gemini models.

- **🔑 Direct Key Link**: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
- **How to Get Your Key**:
  1. Visit [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) and sign in with your Google account.
  2. Click **Create API Key**.
  3. Copy your API key.
- **🌐 Base URL**: `https://generativelanguage.googleapis.com/v1beta/openai`
- **🎯 Recommended Models**:
  - **`gemini-2.5-pro`** *(or `gemini-pro-latest`: Best for full HTML web prototypes & PRDs)*
  - **`gemini-2.5-flash`** *(or `gemini-flash-latest`: Fast for agent panel discussions)*

---

## 🟢 4. OpenAI (ChatGPT / Developer API)

Official OpenAI developer platform for GPT-4o, GPT-4o-mini, and legacy models.

- **🔑 Direct Key Link**: [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys)
- **How to Get Your Key**:
  1. Log in at [https://platform.openai.com/api-keys](https://platform.openai.com/api-keys).
  2. Click **Create new secret key**.
  3. Copy the secret key (starts with `sk-proj-...`).
  4. *Note*: Ensure your account has an active credit balance at [https://platform.openai.com/account/billing](https://platform.openai.com/account/billing).
- **🌐 Base URL**: `https://api.openai.com/v1`
- **🎯 Recommended Models**:
  - **`gpt-4o-mini`** *(Recommended: Excellent balance of performance & cost)*
  - **`gpt-4o`** *(Flagship model)*

---

## 🦙 5. Local LLMs (Ollama / LM Studio — 100% Offline & Free)

Run open-source models completely offline on your computer without an internet connection or paid API key.

### Ollama Setup
- **Download**: [https://ollama.com](https://ollama.com)
- **Run Model**: Open terminal and run `ollama run llama3.3`
- **🌐 Base URL**: `http://localhost:11434/v1`
- **🎯 Model Name**: `llama3.3` *(or `qwen2.5`)*
- **🔑 API Key**: `ollama` *(type any placeholder text)*

### LM Studio Setup
- **Download**: [https://lmstudio.ai](https://lmstudio.ai)
- **Run Model**: Load any model and click **Start Local Server** in the Developer tab.
- **🌐 Base URL**: `http://localhost:1234/v1`
- **🎯 Model Name**: `<model name loaded in LM Studio>`
- **🔑 API Key**: `lm-studio` *(type any placeholder text)*

---

## 🖥️ How to Enter Credentials in the K-Panel UI

1. Open **[http://127.0.0.1:8080/k-panel.html](http://127.0.0.1:8080/k-panel.html)** in your web browser.
2. Click the **Settings (gear icon)** at the top-right corner of the page.
3. Paste your **API Key**, **Base URL**, and **Model Name**.
4. Click **Save**.
5. Start your discussion and generate web prototypes!
