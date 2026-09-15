const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const test = require('node:test');
const vm = require('node:vm');

const rootPath = path.resolve(__dirname, '..');
const appScript = fs.readFileSync(path.join(rootPath, 'app/static/js/app.js'), 'utf8');

function environment(saved, unavailable = false) {
    const root = {dataset: {}, classList: {add() {}}};
    const label = {textContent: ''};
    const icons = ['moon', 'sun'].map(themeIcon => ({dataset: {themeIcon}, hidden: false}));
    const listeners = {};
    const attributes = {};
    const button = {
        querySelector: () => label, querySelectorAll: () => icons,
        setAttribute: (key, value) => { attributes[key] = value; },
        addEventListener: (event, handler) => { listeners[event] = handler; },
    };
    const storage = new Map([['courtstats-theme', saved]]);
    const events = [];
    const context = vm.createContext({
        document: {
            documentElement: root,
            addEventListener: (event, handler) => { if (event === 'DOMContentLoaded') handler(); },
            querySelector: () => null,
            querySelectorAll: selector => selector === '[data-theme-toggle]' ? [button] : [],
        },
        localStorage: {
            getItem(key) { if (unavailable) throw Error('Storage unavailable'); return storage.get(key); },
            setItem(key, value) { storage.set(key, value); },
        },
        window: {
            // No OS query or system change subscription is permitted.
            matchMedia() { throw Error('Theme must not follow the operating system'); },
            dispatchEvent(event) { events.push(event); },
        },
        CustomEvent: class { constructor(type, options) { this.type = type; this.detail = options.detail; } },
    });
    return {context, root, storage, listeners, attributes, icons, label, events};
}

for (const template of ['base', 'login', 'signup']) {
    const source = fs.readFileSync(path.join(rootPath, `app/templates/${template}.html`), 'utf8');
    const init = source.match(/<script>([\s\S]*?)<\/script>/)[1];
    for (const saved of [null, 'invalid', 'light', 'dark']) {
        test(`${template}: saved ${saved} initializes before rendering and persists toggles`, () => {
            const env = environment(saved);
            vm.runInContext(init, env.context);
            const initial = saved === 'dark' ? 'dark' : 'light';
            assert.equal(env.root.dataset.theme, initial);
            vm.runInContext(appScript, env.context);
            env.listeners.click();
            const next = initial === 'dark' ? 'light' : 'dark';
            assert.equal(env.root.dataset.theme, next);
            assert.equal(env.storage.get('courtstats-theme'), next);
            assert.equal(env.attributes['aria-label'], `Switch to ${initial} mode`);
            assert.equal(env.label.textContent, env.attributes['aria-label']);
            assert.equal(env.icons.find(icon => !icon.hidden).dataset.themeIcon, initial === 'dark' ? 'moon' : 'sun');
            assert.equal(env.events[0].type, 'courtstats:themechange');
            assert.equal(env.events[0].detail.theme, next);
            vm.runInContext(init, env.context); // Refresh with the saved choice.
            assert.equal(env.root.dataset.theme, next);
            env.listeners.click();
            assert.equal(env.storage.get('courtstats-theme'), initial);
        });
    }
    test(`${template}: blocked storage defaults to light`, () => {
        const env = environment('dark', true);
        vm.runInContext(init, env.context);
        assert.equal(env.root.dataset.theme, 'light');
    });
}
