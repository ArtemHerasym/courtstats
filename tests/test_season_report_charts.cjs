// Synthetic fixtures test presentation behavior, never published season data.
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');

function harness({ kind = 'comparison', percentage = false, missingLibrary = false, invalid = false, throws = false } = {}) {
    const listeners = {};
    const motion = { matches: false, addEventListener: (name, fn) => { listeners.motion = fn; } };
    const container = { hidden: true };
    const canvas = { parentElement: container };
    const visual = {
        kind, percentage, labels: ['Synthetic A', 'Synthetic B'], units: 'Fixture count', rows: [{ values: [1] }],
        datasets: [{ label: 'Fixture', data: invalid ? ['bad', 2] : [1, null] }],
    };
    const element = { dataset: { reportChart: 'fixture' }, textContent: JSON.stringify(visual) };
    const created = [];
    let dark = false;
    const context = {
        window: { matchMedia: () => motion, addEventListener: (name, fn) => { listeners[name] = fn; } },
        document: {
            documentElement: {},
            getElementById: (id) => id === 'fixture' ? canvas : null,
            querySelectorAll: () => [element],
        },
        getComputedStyle: () => ({ getPropertyValue: () => dark ? '#eeeeee' : '#111111' }),
    };
    if (!missingLibrary) context.Chart = class {
        constructor(target, config) {
            if (throws) throw new Error('Test render failure');
            this.config = config;
            this.destroyed = false;
            created.push(this);
        }
        destroy() { this.destroyed = true; }
    };
    vm.createContext(context);
    for (const file of ['dashboard.js', 'season-report.js']) {
        vm.runInContext(fs.readFileSync(path.join(__dirname, '../app/static/js', file), 'utf8'), context);
    }
    return { created, container, motion, listeners, setDark: () => { dark = true; } };
}

test('chart choice matches comparison, ranking, and chronology', () => {
    for (const [kind, type, axis] of [['comparison', 'bar', 'x'], ['player', 'bar', 'y'], ['progression', 'line', 'x']]) {
        const h = harness({ kind });
        assert.equal(h.created[0].config.type, type);
        assert.equal(h.created[0].config.options.indexAxis, axis);
        assert.equal(h.created[0].config.options.scales[axis === 'x' ? 'y' : 'x'].beginAtZero, true);
        assert.equal(h.created[0].config.data.datasets[0].data[1], null);
        assert.equal(h.container.hidden, false);
    }
});

test('theme and reduced-motion changes rebuild using shared helpers', () => {
    const h = harness();
    h.setDark();
    h.listeners['courtstats:themechange']();
    assert.equal(h.created[0].destroyed, true);
    assert.equal(h.created[1].config.data.datasets[0].borderColor, '#eeeeee');
    h.motion.matches = true;
    h.listeners.motion();
    assert.equal(h.created[1].destroyed, true);
    assert.equal(h.created[2].config.options.animation, false);
});

test('percentage comparisons use the full percentage scale', () => {
    const h = harness({ percentage: true });
    assert.equal(h.created[0].config.options.scales.y.max, 100);
    assert.equal(h.created[0].config.options.scales.y.beginAtZero, true);
});

test('missing library, invalid data, unsupported chart, or render failure leave no broken canvas', () => {
    for (const options of [{ missingLibrary: true }, { invalid: true }, { kind: 'pie' }, { throws: true }]) {
        const h = harness(options);
        assert.equal(h.container.hidden, true);
        assert.equal(h.created.length, 0);
    }
});
