#!/bin/bash
# ============================================================================
# start-in-linux.sh
# ----------------------------------------------------------------------------
# One-click launcher for the K-Panel demo on Linux.
#
# What it does, in order:
#   1. Makes sure Python 3 (+ venv/pip) is installed (installs it via the
#      distro's package manager if missing: apt, dnf, or pacman).
#   2. Creates a local virtual environment (./venv) if it doesn't exist yet.
#   3. Installs/updates the Python dependencies needed by k-panel.py.
#   4. Stops any previous k-panel.py instance still holding the backend port.
#   5. Starts the backend (k-panel.py) on http://127.0.0.1:8877
#   6. Serves k-panel.html on http://127.0.0.1:8080 and opens it in your
#      default browser.
#
# Run it with: ./start-in-linux.sh  (or `bash start-in-linux.sh`)
# ============================================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

BACKEND_PORT=8877
STATIC_PORT=8080

echo "== K-Panel setup (Linux) =="

# --- Step 1: ensure Python 3 (+ venv/pip) is available ---
if ! command -v python3 >/dev/null 2>&1; then
    echo "[setup] Python 3 not found. Attempting to install it..."
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update && sudo apt-get install -y python3 python3-venv python3-pip
    elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y python3 python3-pip
    elif command -v pacman >/dev/null 2>&1; then
        sudo pacman -Sy --noconfirm python python-pip
    else
        echo "[error] Could not detect a supported package manager (apt/dnf/pacman)."
        echo "        Please install Python 3 manually and re-run this script."
        exit 1
    fi
else
    echo "[setup] Python 3 found: $(python3 --version)"
fi

# Some distros ship python3 without the venv module unless installed separately.
if ! python3 -m venv --help >/dev/null 2>&1; then
    echo "[setup] Installing python3-venv..."
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get install -y python3-venv
    fi
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
URL="http://127.0.0.1:$STATIC_PORT/k-panel.html"
if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 || true
else
    echo "[info] Open this URL in your browser: $URL"
fi

echo ""
echo "K-Panel is running:"
echo "  Backend:  http://127.0.0.1:$BACKEND_PORT"
echo "  Frontend: $URL"
echo ""
echo "Press Ctrl+C to stop both servers."

trap "kill $BACKEND_PID $STATIC_PID 2>/dev/null" EXIT
wait
