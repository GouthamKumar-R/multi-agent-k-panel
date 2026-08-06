"""
K-Panel Backend — a *primitive*, hand-rolled "agentic system"
================================================================

This file is intentionally written as a teaching example. It shows, in plain
FastAPI + requests code, the same core ideas that real agentic
frameworks (LangGraph, CrewAI, AutoGen, OpenAI Swarm, etc.) provide with
higher-level abstractions:

    1. AGENT DEFINITIONS   — a persona (system prompt) + metadata, loaded from
                              declarative config files (here: YAML) instead of
                              code. This is what frameworks call an
                              "Agent" or "Assistant" spec.

    2. MODEL CLIENT        — a thin wrapper around calling an LLM API with a
                              system prompt + conversation state and getting
                              text back. Frameworks call this the "LLM
                              provider" / "chat client".

    3. ORCHESTRATION LOOP  — the piece that decides, given the current state
                              (who has spoken, what's been said), which agent
                              should act next, and when the "workflow" is
                              done. This is exactly what a "graph" or "crew"
                              or "planner" does in bigger frameworks — just
                              implemented here as a simple round-robin loop
                              driven by the frontend calling an endpoint
                              repeatedly.

    4. DOWNSTREAM PIPELINE — an example of chaining agent output into a
                              second, larger generation step (turning a
                              multi-agent discussion into a generated
                              artifact — here, a website prototype). This is
                              the same shape as a "tool call" or "pipeline
                              stage" in agentic frameworks: take upstream
                              context, feed it to another prompted LLM call,
                              return a new artifact.

The file is organized in the chronological order a request actually flows
through the system, so you can read it top-to-bottom like a story:
  app boot -> agents load -> a discussion is orchestrated turn-by-turn ->
  a single agent can also be chatted with directly -> the discussion can be
  turned into a generated website.
"""

# ============================================================================
# PHASE 0 — APP SETUP
# ----------------------------------------------------------------------------
# Every agentic system needs a "runtime" it lives inside. Here that runtime is
# just a FastAPI web server. CORS is enabled so our separate frontend
# (running on a different port) is allowed to call these endpoints from the
# browser. Nothing agent-specific happens yet — this is just the web
# framework plumbing every HTTP-based backend needs.
# ============================================================================

import os
import json
import time
import asyncio
import yaml
import requests
import httpx
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "K-Panel Backend is running."}


# ============================================================================
# PHASE 1 — AGENT DEFINITIONS ("the agent registry")
# ----------------------------------------------------------------------------
# In most agentic frameworks, an "Agent" is really just a bundle of:
#   - a persona/identity (name, role, avatar)
#   - a system prompt that tells the LLM how to behave as that persona
#   - some metadata used for discovery/UI (summary, expertise, etc.)
#
# Rather than hardcoding this in Python, we define each agent declaratively in
# a YAML file under backend/agents/*.yaml (one file per expert, e.g.
# brand_manager.yaml, copywriter.yaml, graphic_designer.yaml...). This mirrors
# how frameworks like CrewAI let you define agents in config rather than code
# — it makes it easy to add a new "expert" to the panel without touching any
# orchestration logic: just drop in a new YAML file and restart the server.
#
# Each YAML file has the same shape, and every field is used somewhere later
# in this file:
#
#   id:             stable identifier used everywhere else to refer to this
#                    agent — as the `sender` in a discussion history entry,
#                    the `agent_id` in /chat, and inside `agent_ids` lists.
#   name:            the persona's human name, shown in logs and used to
#                    build the moderator's summary prompt.
#   role:            the job title, shown in the UI's agent picker and used
#                    inside prompts (e.g. "Aarav Patel, a Brand Manager").
#   avatar:          an emoji shown next to the agent in the UI.
#   summary:         one-line description shown in the agent picker list, via
#                    the /agents endpoint below.
#   expertise:       a list of skill tags (currently just metadata for
#                    display — not read anywhere in the backend logic yet).
#   description:     a longer bio (also just metadata / not used by prompts).
#   sample_phrases:  example lines the persona might say (currently just
#                    metadata for display, not fed into any prompt).
#   system_prompt:   *the important one* — this exact string becomes the
#                    {"role": "system", ...} message sent to the LLM every
#                    time this agent takes a turn (see call_agent_llm below).
#                    It defines the persona's voice AND, per our updated
#                    agent files, steers each expert's contribution toward
#                    concrete inputs for the final generated website (e.g.
#                    the Copywriter is told to draft real headline/CTA copy,
#                    the Graphic Designer is told to propose a color palette).
#
# AGENTS is our in-memory "agent registry": a simple list, loaded once at
# startup, that the rest of the system reads from. A production framework
# would likely wrap this in a proper AgentRegistry class with validation,
# hot-reloading, versioning, etc. — but the core idea (a lookup table of agent
# specs) is identical.
# ============================================================================

AGENTS: list[dict] = []


def load_agents() -> None:
    """Load every agent definition (YAML file) from backend/agents/ into AGENTS."""
    global AGENTS
    agents_dir = os.path.join(os.path.dirname(__file__), "agents")
    agents = []
    for filename in os.listdir(agents_dir):
        if filename.endswith(".yaml") or filename.endswith(".yml"):
            with open(os.path.join(agents_dir, filename), "r", encoding="utf-8") as f:
                agent = yaml.safe_load(f)
                agents.append(agent)
    AGENTS = agents


load_agents()


def get_agent_by_id(agent_id: str) -> Optional[dict]:
    """Look up a single agent's full spec (including its system prompt) by id."""
    return next((a for a in AGENTS if a["id"] == agent_id), None)


@app.get("/agents")
def get_agents():
    """List every available agent (summary view only, for building a picker UI)."""
    summaries = [
        {
            "id": a["id"],
            "name": a["name"],
            "role": a["role"],
            "avatar": a["avatar"],
            "summary": a["summary"],
        }
        for a in AGENTS
    ]
    return {"agents": summaries}


@app.get("/agents/{agent_id}")
def get_agent_details(agent_id: str):
    """Get the full definition (including system prompt) for one agent."""
    agent = get_agent_by_id(agent_id)
    if not agent:
        return JSONResponse(status_code=404, content={"error": "Agent not found"})
    return agent


import re


def slugify(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", name.strip().lower()).strip("_")
    return slug or "agent"


@app.post("/agents")
async def create_agent(request: Request):
    """
    Create a brand-new agent at runtime: validate the payload, write it out as
    a YAML file under backend/agents/ (so it persists and survives restarts),
    and immediately add it to the in-memory AGENTS registry (so it's usable
    right away, with no server restart) — true "plug and play" agents.
    """
    body = await request.json()

    name = (body.get("name") or "").strip()
    role = (body.get("role") or "").strip()
    system_prompt = (body.get("system_prompt") or "").strip()
    if not name or not role or not system_prompt:
        return JSONResponse(
            status_code=400,
            content={"error": "name, role, and system_prompt are required."},
        )

    avatar = (body.get("avatar") or "🤖").strip() or "🤖"
    summary = (body.get("summary") or "").strip()
    description = (body.get("description") or "").strip()
    expertise = body.get("expertise") or []
    if isinstance(expertise, str):
        expertise = [e.strip() for e in expertise.split(",") if e.strip()]

    agents_dir = os.path.join(os.path.dirname(__file__), "agents")
    base_id = slugify(body.get("id") or role)
    agent_id = base_id
    suffix = 1
    existing_ids = {a["id"] for a in AGENTS}
    existing_files = set(os.listdir(agents_dir))
    while agent_id in existing_ids or f"{agent_id}.yaml" in existing_files:
        suffix += 1
        agent_id = f"{base_id}_{suffix}"

    agent = {
        "id": agent_id,
        "name": name,
        "role": role,
        "avatar": avatar,
        "summary": summary or f"A {role} on the panel.",
        "expertise": expertise,
        "description": description or f"{name} is a {role}.",
        "sample_phrases": [],
        "system_prompt": system_prompt,
    }

    file_path = os.path.join(agents_dir, f"{agent_id}.yaml")
    with open(file_path, "w", encoding="utf-8") as f:
        yaml.safe_dump(agent, f, sort_keys=False, allow_unicode=True)

    # Hot-reload: add to the live registry immediately, no restart required.
    AGENTS.append(agent)

    return {
        "id": agent["id"],
        "name": agent["name"],
        "role": agent["role"],
        "avatar": agent["avatar"],
        "summary": agent["summary"],
    }


# ============================================================================
# PHASE 2 — THE MODEL CLIENT ("talking to the LLM")
# ----------------------------------------------------------------------------
# Every agentic framework needs a low-level piece that actually calls the
# language model: given a system prompt + conversation messages, send them to
# an LLM API and get text back. Frameworks abstract this behind a
# "ChatModel"/"LLMProvider" interface so agents don't care which model or
# vendor is underneath. Here, that abstraction is just:
#   - resolve_llm_url(...): where to send the request (configurable per call,
#     since each request from the frontend can carry its own proxy/base URL)
#   - print_llm_log(...): a simple observability hook so you can literally
#     watch, in the terminal, every prompt going in and out. Real frameworks
#     call this "tracing" — LangSmith, CrewAI's verbose logging, etc. all do
#     the same thing at a much larger scale.
#
# Notice the pattern that repeats throughout this file:
#   1. build system_prompt (who the agent is) + user_message (what it needs to
#      respond to, including relevant history)
#   2. send {system, user} messages + model name to the LLM API
#   3. parse the text reply out of the response JSON
# That "prompt in, text out" loop is the fundamental unit of an agent turn —
# everything else in this file is about *sequencing* calls to it correctly.
# ============================================================================

# Generic OpenAI-compatible default. Any provider/proxy that implements the
# standard POST {base_url}/chat/completions contract (OpenAI, Azure OpenAI
# gateways, OpenRouter, Together, local vLLM/Ollama-with-OpenAI-shim, internal
# proxies, etc.) works here — just override base_url/model/token per request.
DEFAULT_LLM_BASE_URL = "https://api.openai.com/v1"
DEFAULT_LLM_MODEL = "gpt-5.2"

# Hard output token caps. Regular panel/chat agents only need a short turn of
# dialogue, so they're capped low; the PRD writer gets a bigger budget since it
# has to synthesize the whole discussion into a structured document; the
# website-generation ("visualize") call needs the largest budget since it must
# output a full HTML document.
AGENT_MAX_TOKENS = 2048
PRD_MAX_TOKENS = 10000
# Keep visualization output budget provider-friendly. Very large values (e.g. 100k)
# are rejected by many OpenAI-compatible providers.
VISUALIZE_MAX_TOKENS = PRD_MAX_TOKENS
# Guardrail for very large PRDs to avoid context-window overflow on smaller models.
VISUALIZE_MAX_PRD_CHARS = 18000

# LLM provider rate-limit handling. Keeps transient 429 spikes from failing flows.
LLM_RETRY_MAX_ATTEMPTS = 4
LLM_RETRY_BASE_SECONDS = 1.5
LLM_RETRY_MAX_SECONDS = 12.0


def resolve_llm_url(llm_base_url: Optional[str]) -> str:
    """Normalize a (possibly partial) base URL into a full chat-completions endpoint."""
    url = (llm_base_url or DEFAULT_LLM_BASE_URL).rstrip("/")
    if not url.endswith("/chat/completions"):
        url = f"{url}/chat/completions"
    return url


def describe_http_error(e: Exception, resp: Optional[requests.Response] = None) -> str:
    """Turn an LLM API error into a message that includes the provider's actual
    response body (when available) instead of just "400 Bad Request", since
    that body usually explains exactly what the request got wrong."""
    if resp is not None:
        try:
            body = resp.text.strip()
        except Exception:
            body = ""
        if body:
            return f"Error: {str(e)} — {body[:500]}"
    return f"Error: {str(e)}"


def parse_retry_after_seconds(retry_after: Optional[str]) -> Optional[float]:
    if not retry_after:
        return None
    try:
        delay = float(retry_after.strip())
        if delay >= 0:
            return delay
    except Exception:
        return None
    return None


def retry_delay_seconds(attempt_index: int, retry_after: Optional[str] = None) -> float:
    hinted = parse_retry_after_seconds(retry_after)
    if hinted is not None:
        return min(max(hinted, 0.0), LLM_RETRY_MAX_SECONDS)
    backoff = LLM_RETRY_BASE_SECONDS * (2 ** attempt_index)
    return min(backoff, LLM_RETRY_MAX_SECONDS)


def llm_post_with_retries(url: str, payload: dict, headers: dict, timeout: int) -> requests.Response:
    for attempt in range(LLM_RETRY_MAX_ATTEMPTS):
        try:
            resp = requests.post(
                url,
                json=payload,
                timeout=timeout,
                verify=False,
                headers=headers,
            )
        except requests.RequestException as exc:
            # Fail fast for non-HTTP transport errors to keep UX snappy.
            raise exc

        if resp.status_code != 429:
            resp.raise_for_status()
            return resp

        if attempt == LLM_RETRY_MAX_ATTEMPTS - 1:
            resp.raise_for_status()
        time.sleep(retry_delay_seconds(attempt, resp.headers.get("Retry-After")))

    raise RuntimeError("LLM request failed after retries")


def print_llm_log(persona, system_prompt, user_message, history, endpoint, extra=None):
    """Pretty-print every LLM call to the terminal — a minimal stand-in for
    the "tracing"/"observability" features real agent frameworks provide."""
    print("\n" + "=" * 80)
    print(f"{'LLM CALL LOG':^80}")
    print("=" * 80)
    print(f"{'Endpoint:':<15}{endpoint}")
    print(f"{'Persona:':<15}{persona}")
    print(f"{'System Prompt:':<15}{system_prompt[:200]}{'...' if len(system_prompt) > 200 else ''}")
    print(f"{'User Message:':<15}{user_message[:200]}{'...' if len(user_message) > 200 else ''}")
    print(f"{'History:':<15}")
    if history:
        for m in history:
            sender = m.get("sender", "")
            text = m.get("text", "")
            print(f"  - {sender:<12}: {text[:100]}{'...' if len(text) > 100 else ''}")
    else:
        print("  (none)")
    if extra:
        print(f"{'Extra:':<15}{extra}")
    print("=" * 80 + "\n")


async def call_agent_llm(
    agent,
    topic,
    history,
    llm_token: Optional[str] = None,
    llm_base_url: Optional[str] = None,
    llm_model: Optional[str] = None,
    llm_user: Optional[str] = None,
):
    """Invoke a single agent for one turn: give it the topic + discussion so
    far (as its persona, via system_prompt) and return its reply as plain
    text. This is the "agent.run(context) -> response" primitive that the
    orchestration loop in Phase 3 calls repeatedly."""
    system_prompt = agent.get("system_prompt", "")
    user_message = (
        f"Topic: {topic}\n\nDiscussion so far:\n"
        + "\n".join([f"{m['sender']}: {m['text']}" for m in history])
        + (
            "\n\nRespond briefly, in character for your role, with concrete input that will directly "
            "shape the single-page website prototype generated from this discussion. Avoid generic "
            "advice — give specific, usable details (copy, numbers, colors, structure, etc.) as described "
            "in your role's focus."
        )
    )
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_message},
    ]
    payload = {
        "model": llm_model or DEFAULT_LLM_MODEL,
        "messages": messages,
        "max_tokens": AGENT_MAX_TOKENS,
    }
    if llm_user:
        payload["user"] = llm_user

    print_llm_log(
        persona=f"{agent.get('name', '')} ({agent.get('id', '')})",
        system_prompt=system_prompt,
        user_message=user_message,
        history=history,
        endpoint="/orchestrate",
    )

    try:
        headers = {}
        if llm_token:
            headers["Authorization"] = f"Bearer {llm_token}"
        resp = llm_post_with_retries(
            resolve_llm_url(llm_base_url),
            payload,
            headers,
            timeout=30,
        )
        llm_data = resp.json()
        if "choices" in llm_data and llm_data["choices"]:
            choice = llm_data["choices"][0]
            content = choice.get("message", {}).get("content", "")
            if choice.get("finish_reason") == "length":
                content += " \u26a0\ufe0f *(response truncated — token limit reached)*"
            return content
        elif "response" in llm_data:
            return llm_data["response"]
        return str(llm_data)
    except requests.HTTPError as e:
        return describe_http_error(e, e.response)
    except Exception as e:
        return describe_http_error(e)


# ============================================================================
# PHASE 3 — THE ORCHESTRATION LOOP ("the workflow / the multi-agent graph")
# ----------------------------------------------------------------------------
# This is the heart of the "agentic system": a control loop that decides,
# given the current conversation state, *what happens next*. Real frameworks
# express this as a graph of nodes/edges (LangGraph), a "crew" of agents with
# a manager (CrewAI), or a handoff chain (OpenAI Swarm/Agents SDK). Stripped
# down to its essence, it's always the same three questions, asked on every
# turn:
#
#   1. Is the workflow finished? (has every agent spoken?)
#   2. If not, whose turn is it next? (here: simple round-robin — the first
#      agent in the list who hasn't spoken yet)
#   3. If finished, what's the final output? (here: ask a "moderator" prompt
#      to summarize the whole discussion into a conclusion)
#
# Notice this endpoint is STATELESS on the server: the frontend sends the
# entire conversation history back on every call, and the server just decides
# the *next* step and returns the updated history. This is a common, simple
# pattern for agent orchestration over HTTP — the "state" lives in the
# history array, which is passed back and forth like a baton, rather than
# being kept in server memory/session. It keeps the orchestrator itself
# trivially simple and restart-safe.
# ============================================================================


def prd_writer_system_prompt(agent_names):
    """The persona for the 'PRD writer' role — the one non-panelist agent whose
    job is to synthesize the entire panel discussion into a well-structured
    Product Requirements Document (in Markdown), instead of a short summary."""
    return (
        "You are a senior product manager. You have just observed a panel discussion on a given topic "
        f"among the following experts: {', '.join(agent_names)}. Your job is to synthesize the ENTIRE "
        "discussion — every expert's distinct points, ideas, concerns, and specific details (copy, "
        "numbers, colors, structure, etc.) — into a single, well-structured Product Requirements Document "
        "(PRD) written in clean Markdown.\n\n"
        "The PRD must be thorough and well-organized, using Markdown headings, subheadings, and bullet "
        "lists, and should include AT LEAST these sections:\n"
        "  1. Title & One-Line Summary\n"
        "  2. Overview / Problem Statement\n"
        "  3. Target Audience\n"
        "  4. Value Proposition & Positioning\n"
        "  5. Brand Tone & Personality\n"
        "  6. Key Features / Sections (with concrete details contributed by each expert)\n"
        "  7. Visual Direction (color palette, typography, imagery style)\n"
        "  8. Content & Copy Guidance (headlines, taglines, CTAs, sample copy)\n"
        "  9. Marketing & Growth Considerations\n"
        "  10. Open Questions / Risks\n"
        "  11. Conclusion / Next Steps\n\n"
        "Attribute specific ideas to the expert who raised them where relevant (e.g. 'The Copywriter "
        "suggested...'). Do not omit details — this document is the single source of truth that will be "
        "used downstream to generate a website prototype, so it must capture everything of substance from "
        "the discussion. Output ONLY the Markdown document, with no extra commentary before or after it."
    )


@app.post("/orchestrate")
async def orchestrate_endpoint(request: Request):
    """
    Advance a multi-agent discussion by exactly one step.

    Expects JSON: { "topic": str, "agent_ids": [str], "history": [ { "sender": str, "text": str } ] }

    The frontend calls this endpoint repeatedly (once per turn) until the
    response comes back with status "concluded". Each call:
      - looks at which agents in `agent_ids` have already spoken (by scanning
        `history`)
      - if everyone has spoken -> runs the PRD-writer step (synthesizes the
        whole discussion into a Markdown PRD) and ends the workflow
      - otherwise -> picks the next agent who hasn't spoken, invokes it via
        call_agent_llm(...), appends its reply to history, and returns
    """
    data = await request.json()
    topic = data.get("topic")
    agent_ids = data.get("agent_ids")
    history = data.get("history", [])
    llm_token = data.get("llm_token")
    llm_base_url = data.get("llm_base_url")
    llm_model = data.get("llm_model")
    llm_user = data.get("llm_user")

    if not topic or not agent_ids or not isinstance(agent_ids, list):
        return JSONResponse(status_code=400, content={"error": "Missing topic or agent_ids"})
    if not llm_token:
        return JSONResponse(status_code=401, content={"error": "Missing llm_token"})

    # --- Step 1: has every agent already spoken at least once? ---
    spoken_agents = set(m["sender"] for m in history if m["sender"] in agent_ids)
    remaining_agents = [aid for aid in agent_ids if aid not in spoken_agents]

    # --- Step 2a: workflow finished -> run the PRD-writer step ---
    if not remaining_agents:
        prd_prompt = prd_writer_system_prompt([get_agent_by_id(aid)["name"] for aid in agent_ids])
        prd_user_message = (
            f"Topic: {topic}\n\nFull discussion transcript:\n"
            + "\n".join([f"{m['sender']}: {m['text']}" for m in history])
            + "\n\nWrite the full PRD now, in Markdown, following the required structure."
        )
        prd_messages = [
            {"role": "system", "content": prd_prompt},
            {"role": "user", "content": prd_user_message},
        ]
        print_llm_log(
            persona="PRD Writer",
            system_prompt=prd_prompt,
            user_message=prd_user_message,
            history=history,
            endpoint="/orchestrate (prd writer)",
            extra=f"agent_ids: {agent_ids}",
        )
        payload = {
            "model": llm_model or DEFAULT_LLM_MODEL,
            "messages": prd_messages,
            "max_tokens": PRD_MAX_TOKENS,
        }
        if llm_user:
            payload["user"] = llm_user
        try:
            headers = {}
            if llm_token:
                headers["Authorization"] = f"Bearer {llm_token}"
            resp = llm_post_with_retries(
                resolve_llm_url(llm_base_url),
                payload,
                headers,
                timeout=60,
            )
            llm_data = resp.json()
            if "choices" in llm_data and llm_data["choices"]:
                prd = llm_data["choices"][0].get("message", {}).get("content", "")
            elif "response" in llm_data:
                prd = llm_data["response"]
            else:
                prd = str(llm_data)
        except requests.HTTPError as e:
            prd = describe_http_error(e, e.response)
        except Exception as e:
            prd = describe_http_error(e)

        return {"status": "concluded", "history": history, "prd": prd}

    # --- Step 2b: workflow not finished -> pick the next agent and run it ---
    # A more sophisticated orchestrator could use the LLM itself to *choose*
    # who should speak next (e.g. "which expert's input is most needed now?").
    # Here we keep it simple and deterministic: round-robin in the order the
    # user selected the agents in.
    next_agent_id = remaining_agents[0]
    next_agent = get_agent_by_id(next_agent_id)
    if not next_agent:
        return JSONResponse(status_code=404, content={"error": f"Agent {next_agent_id} not found"})

    agent_reply = await call_agent_llm(next_agent, topic, history, llm_token, llm_base_url, llm_model, llm_user)
    new_message = {"sender": next_agent_id, "text": agent_reply}
    new_history = history + [new_message]

    # --- Step 3: report progress back to the caller ---
    spoken_agents = set(m["sender"] for m in new_history if m["sender"] in agent_ids)
    status = "finalizing" if len(spoken_agents) == len(agent_ids) else "in_progress"

    return {"status": status, "history": new_history, "next_agent": next_agent_id}


@app.post("/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    message = data.get("message")
    agent_id = data.get("agent_id")
    system_prompt = data.get("system_prompt")  # optional override of the agent's persona
    extra_data = data.get("data")  # optional extra context to attach to the payload
    llm_token = data.get("llm_token")
    llm_base_url = data.get("llm_base_url")
    llm_model = data.get("llm_model")
    llm_user = data.get("llm_user")

    stream = request.query_params.get("stream", "0") == "1"

    if not message or not agent_id:
        return JSONResponse(status_code=400, content={"error": "Both 'message' and 'agent_id' are required"})
    if not llm_token:
        return JSONResponse(status_code=401, content={"error": "Missing llm_token"})

    agent = get_agent_by_id(agent_id)
    if not agent:
        return JSONResponse(status_code=404, content={"error": "Agent not found"})

    prompt = system_prompt if system_prompt else agent.get("system_prompt", "")

    print_llm_log(
        persona=f"{agent.get('name', '')} ({agent.get('id', '')})",
        system_prompt=prompt,
        user_message=message,
        history=[],
        endpoint="/chat",
        extra=f"extra_data: {extra_data}" if extra_data else None,
    )

    payload = {
        "model": llm_model or DEFAULT_LLM_MODEL,
        "messages": [
            {"role": "system", "content": prompt},
            {"role": "user", "content": message},
        ],
        "max_tokens": AGENT_MAX_TOKENS,
    }
    if extra_data:
        payload["data"] = extra_data
    if llm_user:
        payload["user"] = llm_user

    # --- Streaming path: forward the LLM's SSE stream straight to the client ---
    if stream:
        payload["stream"] = True
        headers = {}
        if llm_token:
            headers["Authorization"] = f"Bearer {llm_token}"

        async def stream_llm():
            async with httpx.AsyncClient(timeout=60, verify=False) as client:
                for attempt in range(LLM_RETRY_MAX_ATTEMPTS):
                    async with client.stream(
                        "POST",
                        resolve_llm_url(llm_base_url),
                        json=payload,
                        headers=headers,
                    ) as resp:
                        if resp.status_code == 429 and attempt < LLM_RETRY_MAX_ATTEMPTS - 1:
                            await resp.aread()
                            await asyncio.sleep(
                                retry_delay_seconds(attempt, resp.headers.get("Retry-After"))
                            )
                            continue
                        if resp.status_code >= 400:
                            body = await resp.aread()
                            try:
                                body_text = body.decode("utf-8", errors="replace")
                            except Exception:
                                body_text = str(body)
                            err = {
                                "error": f"LLM API error ({resp.status_code}): {body_text[:800]}"
                            }
                            yield f"data: {json.dumps(err)}\n\n"
                            return
                        async for chunk in resp.aiter_text():
                            yield chunk
                        return

        return StreamingResponse(stream_llm(), media_type="text/event-stream")

    # --- Non-streaming path: wait for the full reply and return it as JSON ---
    try:
        headers = {}
        if llm_token:
            headers["Authorization"] = f"Bearer {llm_token}"
        resp = llm_post_with_retries(
            resolve_llm_url(llm_base_url),
            payload,
            headers,
            timeout=30,
        )
        llm_data = resp.json()
        if "choices" in llm_data and llm_data["choices"]:
            reply = llm_data["choices"][0].get("message", {}).get("content", "")
        elif "response" in llm_data:
            reply = llm_data["response"]
        else:
            reply = str(llm_data)
        return {"response": reply}
    except requests.HTTPError as e:
        return JSONResponse(status_code=500, content={"error": f"LLM API error: {describe_http_error(e, e.response)}"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"LLM API error: {describe_http_error(e)}"})


# ============================================================================
# PHASE 4 — DOWNSTREAM PIPELINE ("turning agent output into a generated artifact")
# ----------------------------------------------------------------------------
# This is the final stage of the story: once the panel discussion (Phase 3)
# has produced a rich transcript + summary, we feed *that entire context* into
# one more, larger LLM call whose job is different from any individual
# agent's — it's a "synthesis" step that turns the group's collective input
# into a single generated artifact (here: a self-contained website
# prototype).
#
# This is the same shape as a "tool" or "pipeline stage" in agentic
# frameworks: take upstream conversational context, hand it to a
# purpose-built prompt, and produce a concrete output artifact rather than
# another chat message. The result is streamed back (SSE) so the frontend can
# show the HTML being "typed out" live, just like the chat endpoint above.
# ============================================================================


@app.post("/visualize/stream")
async def visualize_stream_endpoint(request: Request):
    """
    Generate a single-page HTML prototype based on a panel discussion's PRD,
    streaming the raw LLM output (SSE, same shape as /chat?stream=1) so the
    frontend can render the code as it's generated.

    Expects JSON: { "topic": str, "prd": str, "history": [{sender, text}]?,
                    "llm_token": str, "llm_base_url": str?, "llm_model": str? }

    `prd` is the Markdown Product Requirements Document produced by the
    PRD-writer step in /orchestrate — it is the primary input here. `history`
    is accepted only as a fallback for older clients that haven't generated a
    PRD yet.
    """
    data = await request.json()
    topic = data.get("topic")
    prd = data.get("prd", "")
    history = data.get("history", [])
    llm_token = data.get("llm_token")
    llm_base_url = data.get("llm_base_url")
    llm_model = data.get("llm_model")

    if not topic:
        return JSONResponse(status_code=400, content={"error": "Missing topic"})
    if not llm_token:
        return JSONResponse(status_code=401, content={"error": "Missing llm_token"})

    # --- Step 1: fall back to a readable transcript if no PRD was provided ---
    # (keeps this endpoint backward-compatible with older frontend builds)
    def speaker_label(sender_id: str) -> str:
        agent = get_agent_by_id(sender_id)
        if agent:
            return f"{agent.get('name', sender_id)} ({agent.get('role', '')})"
        return sender_id

    if not prd:
        prd = "\n\n".join(
            [f"**{speaker_label(m.get('sender', ''))}:**\n{m.get('text', '')}" for m in history]
        )

    # Provider compatibility guardrail: keep the visualize input bounded.
    if len(prd) > VISUALIZE_MAX_PRD_CHARS:
        prd = (
            prd[:VISUALIZE_MAX_PRD_CHARS]
            + "\n\n[Note: PRD was truncated by the server to fit provider context limits.]"
        )

    # --- Step 2: build the synthesis prompt ---
    # This single prompt does two jobs internally: (a) silently draft a
    # product brief from the PRD, then (b) turn that brief into a finished
    # HTML page. Combining both into one LLM call keeps generation fast (one
    # round trip) instead of two sequential calls.
    system_prompt = (
        "You are a senior product designer and frontend developer who builds award-winning, "
        "content-rich marketing websites (the kind featured on Awwwards/Dribbble). You will be given a "
        "topic and a complete Product Requirements Document (PRD, in Markdown) that was synthesized from "
        "a panel discussion among several named experts. Read the entire PRD carefully — every section "
        "(overview, target audience, value proposition, brand tone, features, visual direction, content "
        "guidance, etc.) should meaningfully shape the final page's content, tone, sections, and "
        "messaging. Pull specific details, arguments, and phrasing directly from the PRD rather than "
        "inventing generic content.\n\n"
        "Using the PRD as your brief, generate a single, long-form, visually stunning, self-contained "
        "HTML page prototype.\n\n"
        "Requirements for your final output:\n"
        "- Output ONLY the raw HTML (no explanations, no markdown code fences, no commentary).\n"
        "- The HTML must be a complete document (<!DOCTYPE html> ... </html>).\n"
        "- You MUST include these exact libraries via CDN in the generated HTML head:\n"
        "  - Tailwind CSS: https://cdn.tailwindcss.com\n"
        "  - Font Awesome 6.5.1: https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.5.1/css/all.min.css\n"
        "  - Google Fonts: Inter and Plus Jakarta Sans\n"
        "- Use inline <style> for custom CSS enhancements in addition to Tailwind utilities (no build tools).\n"
        "- If any interactivity, animation, or UI polish benefits from a JS library (e.g. carousels, "
        "scroll animations, charts), you may include it ONLY via a free, open-source CDN script tag "
        "(e.g. unpkg.com, cdnjs.com, jsdelivr.net) — never invent fake URLs and never use paid/licensed "
        "libraries.\n"
        "- For any images/photos, ONLY use royalty-free sources that work without an API key. Prefer "
        "topic-relevant keyword-based photos via https://source.unsplash.com/featured/?<comma,separated,keywords> "
        "(e.g. https://source.unsplash.com/featured/?coffee,shop for a cafe hero image) so images actually "
        "match the page's subject matter. Use https://picsum.photos/<width>/<height>?random=<n> only as a "
        "generic fallback when no topical keywords make sense. Never reference local files, fake paths, or "
        "placeholder text like 'image.jpg'. Prefer CSS gradients/shapes/icons over images where a photo "
        "isn't essential.\n"
        "- The page MUST be long-form and detailed, including AT LEAST the following sections, each fully "
        "fleshed out with realistic, specific mock content (never placeholder lorem-ipsum or generic "
        "'Feature 1/2/3' text):\n"
        "  1. A sticky/top navigation bar with logo + nav links + a CTA button.\n"
        "  2. A bold hero section with a compelling headline, subheadline, primary + secondary CTA "
        "buttons, and a supporting visual built with CSS (illustration, gradient blob, mockup shape, etc).\n"
        "  3. A logo/trust bar of well-known-sounding partner or client names.\n"
        "  4. A features/benefits section with at least 4-6 distinct feature cards, each with an icon "
        "(inline SVG or icon-font glyph), a specific title, and 1-2 sentences of real, concrete detail.\n"
        "  5. A 'how it works' or process section with numbered steps.\n"
        "  6. A stats/metrics section with several specific, impressive-sounding numbers (e.g. '10,000+ "
        "users', '4.9/5 rating').\n"
        "  7. A testimonials/social-proof section with at least 3 realistic quotes, names, and roles.\n"
        "  8. A pricing section with at least 2-3 pricing tiers, each listing specific included features.\n"
        "  9. An FAQ section with at least 4-5 real question/answer pairs relevant to the topic.\n"
        "  10. A strong final call-to-action section.\n"
        "  11. A detailed footer with multiple link columns, social icons, and a copyright line.\n"
        "- Every section must contain real, specific, on-topic mock data tailored to the PRD — never "
        "generic filler text.\n"
        f"- You have a strict output budget of approximately {VISUALIZE_MAX_TOKENS} tokens. Plan the page "
        "so it is fully complete within that budget: keep prose concise, avoid redundant markup, and "
        "always return a valid, finished HTML document (never partial/truncated output).\n"
        "- Visual style requirements: modern glassmorphism, layered gradients, soft backdrop blur, card hover "
        "effects, subtle shadows, and tasteful CSS animations/transitions.\n"
        "- Typography requirements: Inter and Plus Jakarta Sans with clear hierarchy and strong readability.\n"
        "- Use semantic HTML5 elements and ensure the layout is responsive (flexbox/grid + media queries)."
    )
    user_message = (
        f"Topic: {topic}\n\n"
        f"FULL PRODUCT REQUIREMENTS DOCUMENT (use every section below, not just the overview):\n"
        f"{prd}\n\n"
        "Generate the HTML now, making sure the content reflects specific details from every section of "
        "the PRD above."
    )
    print_llm_log(
        persona="Visualizer",
        system_prompt=system_prompt,
        user_message=user_message,
        history=history,
        endpoint="/visualize/stream",
    )


    # --- Step 3: stream the generation back to the frontend as it's produced ---
    payload = {
        "model": llm_model or DEFAULT_LLM_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "stream": True,
        "max_tokens": VISUALIZE_MAX_TOKENS,
    }
    if data.get("llm_user"):
        payload["user"] = data.get("llm_user")
    headers = {}
    if llm_token:
        headers["Authorization"] = f"Bearer {llm_token}"

    async def stream_llm():
        async with httpx.AsyncClient(timeout=120, verify=False) as client:
            for attempt in range(LLM_RETRY_MAX_ATTEMPTS):
                async with client.stream(
                    "POST",
                    resolve_llm_url(llm_base_url),
                    json=payload,
                    headers=headers,
                ) as resp:
                    if resp.status_code == 429 and attempt < LLM_RETRY_MAX_ATTEMPTS - 1:
                        await resp.aread()
                        await asyncio.sleep(
                            retry_delay_seconds(attempt, resp.headers.get("Retry-After"))
                        )
                        continue
                    if resp.status_code >= 400:
                        body = await resp.aread()
                        try:
                            body_text = body.decode("utf-8", errors="replace")
                        except Exception:
                            body_text = str(body)
                        err = {
                            "error": f"LLM API error ({resp.status_code}): {body_text[:800]}"
                        }
                        yield f"data: {json.dumps(err)}\n\n"
                        return
                    async for chunk in resp.aiter_text():
                        yield chunk
                    return

    return StreamingResponse(stream_llm(), media_type="text/event-stream")


# ============================================================================
# ENTRY POINT — `python k-panel.py`
# ----------------------------------------------------------------------------
# Because this file's name contains a hyphen, it can't be imported as a
# module (e.g. `uvicorn k-panel:app` would fail), so we run the server
# programmatically here instead. This is what the start-in-*.sh/.bat launcher
# scripts invoke directly.
# ============================================================================

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8877)

