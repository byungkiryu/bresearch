"""Exercise the shipped browser code without a browser or external packages."""
import json
from pathlib import Path
import shutil
import subprocess
import unittest


REPO = Path(__file__).resolve().parents[1]
NODE = shutil.which("node")

# Run the complete app with small DOM stand-ins. Only the closure's final line is
# instrumented to expose its state; rendering and delegated handlers are real.
HARNESS = r"""
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const request = JSON.parse(fs.readFileSync(0, 'utf8'));
const nodes = new Map();
function node(id = '') {
  return { id, innerHTML: '', textContent: '', listeners: {}, dataset: {},
    classList: { toggle() {}, add() {}, remove() {} },
    addEventListener(type, handler) { this.listeners[type] = handler; },
    setAttribute() {}, removeAttribute() {}, querySelector() { return null; },
    querySelectorAll() { return []; }, focus() {}, close() { this.open = false; },
    showModal() { this.open = true; },
  };
}
for (const id of ['app', 'detail-dialog', 'detail-content', 'toast', 'dialog-close',
                  'result-count', 'catalog-results', 'catalog-more', 'news-count', 'news-results']) {
  nodes.set(id, node(id));
}
const location = { _hash: '#publications', hostname: 'localhost', pathname: '/',
  get hash() { return this._hash; },
  set hash(value) { this._hash = value.startsWith('#') ? value : '#' + value; },
};
const window = { HOMEPAGE_DATA: request.data, listeners: {},
  addEventListener(type, handler) { this.listeners[type] = handler; }, scrollTo() {},
};
const context = vm.createContext({ window, location, URL, URLSearchParams, assert,
  navigator: {}, setTimeout, clearTimeout, nodes,
  history: { replaceState(_state, _unused, value) { location.hash = value; } },
  document: { title: '', getElementById(id) { return nodes.get(id) || null; },
    querySelector() { return null; }, querySelectorAll() { return []; },
  },
});
const source = fs.readFileSync(request.source, 'utf8');
const exposed = source.replace(/\}\)\(\);\s*$/, `
  globalThis.display = { authorName, authorsHtml, citation, recordNumbers, publications,
    presentations, state, matchingRecords, catalogueGroups, updateCatalogue,
    renderNews, updateNews, newsItems, renderPage };
})();`);
assert.notEqual(exposed, source, 'App closure instrumentation must succeed');
vm.runInContext(exposed, context, { filename: request.source });
vm.runInContext(`
  function clickButton(dataset) {
    const target = { dataset,
      closest() { return this; },
      hasAttribute(name) {
        const key = name.replace(/^data-/, '').replace(/-([a-z])/g, (_, c) => c.toUpperCase());
        return Object.hasOwn(dataset, key);
      },
    };
    nodes.get('app').listeners.click({ target });
  }
  function changeEvent(value) {
    nodes.get('app').listeners.change({ target: {
      dataset: { catalog: 'presentations', filter: 'eventId' }, value,
      matches(selector) { return selector === 'select[data-catalog]'; },
    }});
  }
`, context);
vm.runInContext(request.test, context, { filename: 'frontend-regression.js' });
"""


@unittest.skipUnless(NODE, "Node.js is required for browser JavaScript checks")
class FrontendDisplayTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        def read(relative):
            return json.loads((REPO / relative).read_text(encoding="utf-8"))
        cls.real_data = {
            "publications": read("data/publications.json"),
            "presentations": read("data/presentations.json"),
            "content": read("content/items.json"),
            "site": read("content/site.json"),
        }

    def run_js(self, test, data=None):
        result = subprocess.run(
            [NODE, "-e", HARNESS],
            input=json.dumps({"source": str(REPO / "src/app.js"),
                              "data": data if data is not None else self.real_data,
                              "test": test}, ensure_ascii=False),
            text=True, capture_output=True, timeout=20,
        )
        self.assertEqual(result.returncode, 0, result.stderr or result.stdout)

    def test_hangul_names_keep_source_order_and_english_names_keep_spelling(self):
        self.run_js(r"""
          for (const [raw, expected] of [
            ['류, 병기', '류병기'], ['손, 지희', '손지희'], ['정, 재환', '정재환'],
            ['남궁, 민수', '남궁민수'], ['류, 병 기', '류병기'],
            ['Ryu, Byungki', 'Byungki Ryu'], ['Son, Jihui', 'Jihui Son'],
            ['Bhattacharjee, Dipanwita', 'Dipanwita Bhattacharjee'],
            ['류병기', '류병기'], ['Research Group', 'Research Group'],
          ]) assert.equal(display.authorName(raw), expected);
          const record = display.presentations.find(row => row.id === 'talk-0159');
          assert.ok(record.authors.includes('류, 병기'), 'Keep Zotero source names unchanged');
          const authors = display.authorsHtml(record.authors);
          assert.ok(authors.includes('손지희, 장정인, 박종호, 정재환, 박수동'));
          assert.ok(authors.includes('<strong class="author-highlight">류병기</strong>'));
          assert.ok(display.citation(record).includes('류병기'));
          assert.ok(!display.citation(record).includes('병기 류'));
          display.state.presentations.query = '류병기';
          assert.ok(display.matchingRecords('presentations').some(row => row.id === record.id));
        """)

    def test_cumulative_numbers_follow_chronology_and_survive_filters(self):
        self.run_js(r"""
          for (const catalog of ['publications', 'presentations']) {
            const rows = display[catalog];
            const chronological = [...rows].sort((a, b) =>
              b.date.localeCompare(a.date) || b.id.localeCompare(a.id));
            assert.equal(rows.map(row => row.id).join(), chronological.map(row => row.id).join());
            rows.forEach((row, index) =>
              assert.equal(display.recordNumbers.get(row.id), rows.length - index));
            display.state[catalog].year = String(rows[Math.floor(rows.length / 2)].year);
            const filtered = display.matchingRecords(catalog);
            assert.ok(filtered.length > 0 && filtered.length < rows.length);
            filtered.forEach(row => assert.equal(display.recordNumbers.get(row.id),
              rows.length - rows.findIndex(candidate => candidate.id === row.id)));
            display.updateCatalogue(catalog);
            assert.ok(nodes.get('catalog-results').innerHTML.includes(
              'aria-label="Record number ' + display.recordNumbers.get(filtered[0].id) + '"'));
          }
          assert.ok(display.recordNumbers.get('talk-0158') > display.recordNumbers.get('talk-0159'),
            'Stable source ID suffixes are not chronological display numbers');
        """)

    def test_year_groups_and_load_more_do_not_duplicate_boundary_heading(self):
        rows = [{"id": f"pub-{index:04}", "kind": "publication", "item_type": "journalArticle",
                 "title": f"Paper {index}", "authors": ["Ryu, Byungki"],
                 "year": 2026 if index < 21 else 2025,
                 "date": f"{2026 if index < 21 else 2025}-01-01"}
                for index in range(23)]
        self.run_js(r"""
          const headings = () => [...nodes.get('catalog-results').innerHTML.matchAll(
            /class="catalog-year-heading">([^<]+)/g)].map(match => match[1]);
          assert.equal(headings().join(), '2026');
          assert.equal((nodes.get('catalog-results').innerHTML.match(/data-record-id=/g) || []).length, 20);
          clickButton({ loadMore: 'publications' });
          assert.equal(headings().join(), '2026,2025');
          const html = nodes.get('catalog-results').innerHTML;
          assert.equal((html.match(/data-record-id=/g) || []).length, 23);
          assert.ok(html.includes('aria-label="Record number 23"'));
          assert.ok(html.includes('aria-label="Record number 1"'));
          assert.equal(nodes.get('catalog-more').innerHTML, '');
        """, {"publications": rows, "presentations": []})

    def test_combined_news_events_filter_and_related_presentation_navigation(self):
        self.run_js(r"""
          location.hash = '#news';
          display.renderPage();
          assert.equal(display.state.news.type, 'all');
          let html = nodes.get('news-results').innerHTML;
          assert.ok(html.includes('Latest event') && html.includes('Group news'));
          assert.ok(html.indexOf('Latest event') < html.indexOf('Group news'));
          assert.ok(!html.includes('Hidden event'));
          clickButton({ newsView: 'events' });
          assert.equal(location.hash, '#news?view=events');
          html = nodes.get('news-results').innerHTML;
          assert.ok(html.includes('Latest event') && !html.includes('Group news'));
          assert.ok(html.includes('data-event-records="event-a"'));
          clickButton({ eventRecords: 'event-a' });
          assert.equal(location.hash, '#presentations?event=event-a');
          window.listeners.hashchange();
          assert.equal(display.state.page, 'presentations');
          assert.equal(display.matchingRecords('presentations').map(row => row.id).join(), 'talk-a');
          assert.ok(!nodes.get('app').innerHTML.includes('data-news-view'));
          changeEvent('event-b');
          assert.equal(location.hash, '#presentations?event=event-b');
          assert.equal(display.matchingRecords('presentations').map(row => row.id).join(), 'talk-b');
          clickButton({ clearCatalog: 'presentations' });
          assert.equal(location.hash, '#presentations');
          assert.equal(display.matchingRecords('presentations').length, 2);
          display.renderPage();
          assert.equal(display.matchingRecords('presentations').length, 2);
        """, {
            "publications": [],
            "presentations": [
                {"id": "talk-a", "kind": "presentation", "year": 2026, "date": "2026-02-01", "authors": [], "title": "Talk A"},
                {"id": "talk-b", "kind": "presentation", "year": 2025, "date": "2025-02-01", "authors": [], "title": "Talk B"},
            ],
            "content": {"items": {"talk-a": {"event_id": "event-a"}, "talk-b": {"event_id": "event-b"}}},
            "site": {
                "news": [{"id": "news-a", "title": "Group news", "date": "2026-01-01"}],
                "events": [
                    {"id": "event-b", "title": "Earlier event", "start_date": "2025-02-01"},
                    {"id": "event-a", "title": "Latest event", "start_date": "2026-02-01"},
                    {"id": "event-hidden", "title": "Hidden event", "start_date": "2027-01-01", "public": False},
                ],
            },
        })


if __name__ == "__main__":
    unittest.main()
