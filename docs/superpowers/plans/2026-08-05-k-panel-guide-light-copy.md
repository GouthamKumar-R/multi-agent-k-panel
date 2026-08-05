# K-Panel Guide Light Theme and Copy Controls Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish an always-light five-step K-Panel guide with accessible one-click copying for every command block.

**Architecture:** Keep the guide as one standalone HTML artifact. CSS variables and component surfaces provide the light visual system; dependency-free JavaScript discovers command cards, adds copy buttons, and handles Clipboard API and fallback copying without affecting step navigation.

**Tech Stack:** HTML5, CSS, browser JavaScript, Node.js built-in test runner.

## Global Constraints

- The page is always light; no theme toggle or system-theme switching.
- Preserve the five-step layout, responsive navigation, logos, print output, reduced-motion support, forced-colors support, and no-JavaScript fallback.
- Add a copy control to every `.command` containing a `<pre><code>` block.
- Keep the artifact standalone with no new libraries or network dependencies.
- Copy plain text exactly, preserving command line breaks.

## File Structure

- Create `tests/setup-guide-copy.test.js`: executable light-theme and copy-interaction contract.
- Modify `docs/KPANEL_SETUP_EXECUTIVE.html`: light palette, copy button styling, Clipboard API integration, fallback, and accessible feedback.

---

### Task 1: Light Guide and Command Copy Controls

**Files:**
- Create: `tests/setup-guide-copy.test.js`
- Modify: `docs/KPANEL_SETUP_EXECUTIVE.html:15-204`
- Modify: `docs/KPANEL_SETUP_EXECUTIVE.html:338-378`

**Interfaces:**
- Consumes: each `.command` element's nested `<pre><code>` text.
- Produces: `copyText(text): Promise<boolean>` and one `.copy-button` per command block.

- [ ] **Step 1: Write the failing behavior test**

Create `tests/setup-guide-copy.test.js`:

```javascript
const assert = require("node:assert/strict");
const fs = require("node:fs");
const test = require("node:test");
const vm = require("node:vm");

const html = fs.readFileSync("docs/KPANEL_SETUP_EXECUTIVE.html", "utf8");
const script = [...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].at(-1)[1];

function loadGuideScript() {
  const handlers = {};
  const timers = [];
  const created = [];
  const code = { textContent: "chmod +x start-in-mac.sh\n./start-in-mac.sh" };
  const label = { textContent: "Run one platform command" };
  const command = {
    children: [],
    querySelector(selector) {
      if (selector === "pre code") return code;
      if (selector === ".label") return label;
      return null;
    },
    append(node) { this.children.push(node); },
  };
  const body = {
    children: [],
    append(node) { this.children.push(node); },
  };
  const document = {
    body,
    querySelectorAll(selector) {
      if (selector === ".command") return [command];
      return [];
    },
    querySelector() { return null; },
    createElement(tag) {
      const node = {
        tag,
        dataset: {},
        style: {},
        textContent: "",
        setAttribute(name, value) { this[name] = value; },
        addEventListener(name, handler) { handlers[name] = handler; },
        select() { this.selected = true; },
        remove() { this.removed = true; },
      };
      created.push(node);
      return node;
    },
    execCommand() { return true; },
  };
  const writes = [];
  const context = vm.createContext({
    document,
    navigator: { clipboard: { async writeText(text) { writes.push(text); } } },
    window: { matchMedia: () => ({ matches: false }) },
    setTimeout(callback) { timers.push(callback); return timers.length; },
    clearTimeout() {},
    WeakMap,
  });
  vm.runInContext(script, context);
  return { body, command, context, created, handlers, timers, writes };
}

test("uses an always-light visual palette", () => {
  assert.match(html, /--bg:\s*#f4f7fb/);
  assert.match(html, /--surface:\s*#ffffff/);
  assert.match(html, /--text:\s*#172033/);
  assert.doesNotMatch(html, /--bg:\s*#070b16/);
});

test("adds an accessible copy button and copies exact command text", async () => {
  const guide = loadGuideScript();
  const button = guide.command.children.find((node) => node.className === "copy-button");
  assert.ok(button);
  assert.equal(button.type, "button");
  assert.match(button["aria-label"], /^Copy /);
  await guide.handlers.click();
  assert.deepEqual(guide.writes, ["chmod +x start-in-mac.sh\n./start-in-mac.sh"]);
  assert.equal(button.textContent, "Copied");
  assert.equal(guide.body.children[0]["aria-live"], "polite");
});

test("falls back to a temporary textarea when Clipboard API rejects", async () => {
  const guide = loadGuideScript();
  guide.context.navigator.clipboard.writeText = async () => { throw new Error("blocked"); };
  assert.equal(await guide.context.copyText("python3 --version"), true);
  const textarea = guide.created.find((node) => node.tag === "textarea");
  assert.equal(textarea.value, "python3 --version");
  assert.equal(textarea.selected, true);
  assert.equal(textarea.removed, true);
});

test("defines failure feedback and hides copy controls when printing", () => {
  assert.match(html, /Copy failed/);
  assert.match(html, /@media print[\s\S]*?\.copy-button\s*\{\s*display:\s*none/);
});
```

- [ ] **Step 2: Run the test and verify RED**

Run:

```bash
node --test tests/setup-guide-copy.test.js
```

Expected: failures for the missing light palette and copy controls. The failures must reference assertions such as `--bg: #f4f7fb` or a missing `.copy-button`, not a test syntax error.

- [ ] **Step 3: Implement the light visual system**

In `docs/KPANEL_SETUP_EXECUTIVE.html`, replace the root palette with:

```css
:root {
  --bg: #f4f7fb;
  --surface: #ffffff;
  --raised: #f8fafd;
  --line: #dbe4f0;
  --text: #172033;
  --muted: #5f6f86;
  --cyan: #0067c5;
  --violet: #6647c7;
  --green: #16794a;
  --amber: #9a5b00;
}
```

Update the existing dark surfaces to use the variables above. Use pale blue and violet body gradients, `var(--surface)` for `.hero` and `.step-panel`, a light navy shadow, `#18324f` for command/provider code, and a white-to-pale-blue provider-card gradient. Give `.brand-logo.right` a dark navy background and internal padding so the existing white Nasscom logo remains visible.

Add these copy-control styles near the command styles:

```css
.command { position: relative; }
.command .label { padding-right: 88px; }
.copy-button {
  position: absolute;
  top: 11px;
  right: 11px;
  padding: 7px 10px;
  border: 1px solid #b9cce2;
  border-radius: 8px;
  color: var(--cyan);
  background: var(--surface);
  font: 750 .72rem/1 ui-sans-serif, system-ui, sans-serif;
  cursor: pointer;
}
.copy-button:hover { border-color: var(--cyan); background: #eef6ff; }
.copy-button:focus-visible { outline: 2px solid var(--cyan); outline-offset: 2px; }
.copy-button[data-state="success"] { color: var(--green); border-color: #9bd1b7; background: #eefaf4; }
.copy-button[data-state="error"] { color: #a23b32; border-color: #e3aaa5; background: #fff4f2; }
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
```

Inside `@media print`, add:

```css
.copy-button { display: none; }
```

- [ ] **Step 4: Implement copy behavior and feedback**

Append this code after the existing step-navigation setup:

```javascript
const copyResetTimers = new WeakMap();
const copyAnnouncement = document.createElement("div");
copyAnnouncement.className = "sr-only";
copyAnnouncement.setAttribute("aria-live", "polite");
document.body.append(copyAnnouncement);

async function copyText(text) {
  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(text);
      return true;
    } catch {
      // Continue to the browser-compatible fallback.
    }
  }
  const textarea = document.createElement("textarea");
  textarea.value = text;
  textarea.setAttribute("readonly", "");
  textarea.style.position = "fixed";
  textarea.style.opacity = "0";
  document.body.append(textarea);
  textarea.select();
  try {
    return document.execCommand("copy");
  } catch {
    return false;
  } finally {
    textarea.remove();
  }
}

function showCopyStatus(button, message, state) {
  button.textContent = message;
  button.dataset.state = state;
  copyAnnouncement.textContent = message;
  clearTimeout(copyResetTimers.get(button));
  copyResetTimers.set(button, setTimeout(() => {
    button.textContent = "Copy";
    delete button.dataset.state;
  }, 1600));
}

document.querySelectorAll(".command").forEach((command) => {
  const code = command.querySelector("pre code");
  if (!code) return;
  const label = command.querySelector(".label")?.textContent.trim() || "command";
  const button = document.createElement("button");
  button.type = "button";
  button.className = "copy-button";
  button.textContent = "Copy";
  button.setAttribute("aria-label", `Copy ${label}`);
  button.addEventListener("click", async () => {
    const copied = await copyText(code.textContent);
    showCopyStatus(button, copied ? "Copied" : "Copy failed", copied ? "success" : "error");
  });
  command.append(button);
});
```

- [ ] **Step 5: Run automated verification and verify GREEN**

Run:

```bash
node --test tests/setup-guide-copy.test.js
python3 - <<'PY'
from html.parser import HTMLParser
from pathlib import Path

path = Path("docs/KPANEL_SETUP_EXECUTIVE.html")
text = path.read_text()

class GuideParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.steps = 0
        self.panels = 0
        self.images = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "button" and "step-trigger" in attrs.get("class", "").split():
            self.steps += 1
        if tag == "section" and attrs.get("id", "").startswith("panel-step-"):
            self.panels += 1
        if tag == "img":
            self.images.append(attrs["src"])

parser = GuideParser()
parser.feed(text)
assert parser.steps == parser.panels == 5
assert "prefers-reduced-motion: reduce" in text
assert "forced-colors: active" in text
assert "display: block !important" in text
for image in parser.images:
    assert (path.parent / image).exists(), image
print("Guide structure and local assets verified.")
PY
git diff --check
```

Expected: four Node tests pass, the structural script prints `Guide structure and local assets verified.`, and `git diff --check` exits with no output.

- [ ] **Step 6: Commit the implementation**

```bash
git add tests/setup-guide-copy.test.js docs/KPANEL_SETUP_EXECUTIVE.html
git commit -m "Add light guide and command copy controls"
```

- [ ] **Step 7: Publish and verify GitHub Pages**

Push the branch, create a pull request against `main`, merge it, wait for the GitHub Pages build to report `built`, and fetch:

```text
https://gouthamkumar-r.github.io/multi-agent-k-panel/KPANEL_SETUP_EXECUTIVE.html
```

Confirm the fetched artifact contains the light theme and `Copy` control implementation.
