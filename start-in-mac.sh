#!/bin/bash
# ============================================================================
# start-in-mac.sh
# ----------------------------------------------------------------------------
# One-click launcher for the K-Panel demo on macOS.
#
# What it does, in order:
#   1. Makes sure Python 3 is installed (installs it via Homebrew if missing).
#   2. Creates a local virtual environment (./venv) if it doesn't exist yet.
#   3. Installs/updates the Python dependencies needed by k-panel.py.
#   4. Stops any previous k-panel.py instance still holding the backend port.
#   5. Starts the backend (k-panel.py) on http://127.0.0.1:8877
#   6. Serves k-panel.html on http://127.0.0.1:8080 and opens it in your
#      default browser.
#
# Just double-click this file (or run `./start-in-mac.sh` in Terminal).
# ============================================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

BACKEND_PORT=8877
STATIC_PORT=8080

echo "== K-Panel setup (macOS) =="

# --- Step 1: ensure Python 3 is available ---
if ! command -v python3 >/dev/null 2>&1; then
    echo "[setup] Python 3 not found."
    if command -v brew >/dev/null 2>&1; then
        echo "[setup] Installing Python 3 via Homebrew..."
        brew install python3
    else
        echo "[setup] Homebrew not found. Installing Homebrew first..."
        /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
        echo "[setup] Installing Python 3 via Homebrew..."
        brew install python3
    fi
else
    echo "[setup] Python 3 found: $(python3 --version)"
fi

# --- Step 2: create a virtual environment if missing ---
if [ ! -d "$DIR/venv" ]; then
    echo "[setup] Creating virtual environment..."
    python3 -m venv "$DIR/venv"
fi

# --- Step 3: install/update Python dependencies ---
echo "[setup] Installing Python dependencies..."
"$DIR/venv/bin/pip" install --quiet --disable-pip-version-check --upgrade pip
"$DIR/venv/bin/pip" install --quiet --disable-pip-version-check -r "$DIR/requirements.txt"

# --- Step 4: start the backend (FastAPI/uvicorn) ---
# Port 8877 was chosen specifically because it isn't a well-known default for
# any common service (unlike, say, 5432 which is PostgreSQL's default port).
# To keep re-runs of this script safe, we only stop a *previous instance of
# our own backend* (matched by its command line containing "k-panel.py"),
# never an arbitrary/unrelated process that might happen to be using the
# port — that avoids accidentally killing something like a real database.
EXISTING_PID=$(pgrep -f "[k]-panel.py" || true)
if [ -n "$EXISTING_PID" ]; then
    echo "[setup] Stopping a previous K-Panel backend instance (pid $EXISTING_PID)..."
    kill $EXISTING_PID 2>/dev/null || true
    sleep 1
fi

echo "[run] Starting backend on http://127.0.0.1:$BACKEND_PORT ..."
"$DIR/venv/bin/python" "$DIR/k-panel.py" > "$DIR/backend.log" 2>&1 &
BACKEND_PID=$!
echo "$BACKEND_PID" > "$DIR/.backend.pid"

# --- Step 5: serve the static HTML page and open it in the browser ---
echo "[run] Serving k-panel.html on http://127.0.0.1:$STATIC_PORT ..."
"$DIR/venv/bin/python" -m http.server $STATIC_PORT --directory "$DIR" > "$DIR/static.log" 2>&1 &
STATIC_PID=$!
echo "$STATIC_PID" > "$DIR/.static.pid"

sleep 2
open "http://127.0.0.1:$STATIC_PORT/k-panel.html" 2>/dev/null || true

echo ""
echo "K-Panel is running:"
echo "  Backend:  http://127.0.0.1:$BACKEND_PORT"
echo "  Frontend: http://127.0.0.1:$STATIC_PORT/k-panel.html"
echo ""
echo "Press Ctrl+C to stop both servers."

trap "kill $BACKEND_PID $STATIC_PID 2>/dev/null" EXIT
wait
