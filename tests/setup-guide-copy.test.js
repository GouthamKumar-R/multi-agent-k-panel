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
