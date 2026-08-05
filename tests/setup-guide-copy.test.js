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
  const code = { textContent: "./start-in-mac.sh" };
  const commandLine = {
    children: [],
    querySelector(selector) {
      if (selector === "code") return code;
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
      if (selector === ".command-line") return [commandLine];
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
  return { body, commandLine, context, created, handlers, timers, writes };
}

test("uses an always-light visual palette", () => {
  assert.match(html, /--bg:\s*#f4f7fb/);
  assert.match(html, /--surface:\s*#ffffff/);
  assert.match(html, /--text:\s*#172033/);
  assert.doesNotMatch(html, /--bg:\s*#070b16/);
});

test("adds one accessible copy button for an individual command", async () => {
  const guide = loadGuideScript();
  const button = guide.commandLine.children.find((node) => node.className === "copy-button");
  assert.ok(button);
  assert.equal(button.type, "button");
  assert.match(button["aria-label"], /^Copy /);
  await guide.handlers.click();
  assert.deepEqual(guide.writes, ["./start-in-mac.sh"]);
  assert.equal(button.textContent, "Copied");
  assert.equal(guide.body.children[0]["aria-live"], "polite");
});

test("renders individual copy rows only for shell commands", () => {
  assert.equal((html.match(/class="command-line"/g) || []).length, 9);
  assert.doesNotMatch(html, /class="command"[\s\S]*?<pre><code>/);
});

test("shows both white logos and the approved step structure", () => {
  assert.match(html, /\.brand-logo\s*\{[^}]*background:\s*#18324f/s);
  assert.match(html, /Launch Multi-Agent Blueprint from your operating system/);
  assert.match(html, /Run the multi-agent panel and visualize the PRD/);
  assert.match(html, /Optional: Create a custom persona agent/);
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
