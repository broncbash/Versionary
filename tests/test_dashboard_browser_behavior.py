"""Headless Chromium behavioral tests for the Versionary dashboard.

No external Python or JavaScript packages required.
All agents, credentials and API responses are simulated.
"""

import json
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from dashboard_ui import PAGE


BROWSER_TESTS = r"""
'use strict';

const output = document.createElement('pre');
output.id = 'browser-test-results';
document.body.append(output);

const results = [];

function assert(condition, description) {
  if (!condition) {
    throw new Error(description);
  }
}

function deferred() {
  let resolve;
  let reject;
  const promise = new Promise((yes, no) => {
    resolve = yes;
    reject = no;
  });
  return {promise, resolve, reject};
}

const requests = [];

window.fetch = (url, options) => {
  const request = deferred();
  requests.push({
    url: String(url),
    options,
    ...request
  });
  return request.promise;
};

window.confirm = () => true;
window.prompt = () => null;

function agent(status = 'pending') {
  return {
    id: 'test-agent-001',
    hostname: 'simulated-agent',
    platform: 'arch',
    distro_id: 'arch',
    distro_name: 'Arch Linux',
    status,
    health: 'no_contact',
    scan_status: null,
    updates: null,
    last_seen: null,
    scan_at: null
  };
}

function response(agents) {
  return {
    ok: true,
    status: 200,
    json: async () => ({agents})
  };
}

async function flush() {
  await new Promise(resolve => setTimeout(resolve, 0));
}

function click(id) {
  document.getElementById(id).click();
}

function reset() {
  click('clear');
  requests.length = 0;
  document.getElementById('token').value = 'SIMULATED_TOKEN';
}

async function loadFleet(agents) {
  click('refresh');

  assert(requests.length === 1, 'Expected inventory request');
  assert(
    requests[0].url === '/api/v1/admin/agents',
    'Unexpected inventory endpoint'
  );

  requests[0].resolve(response(agents));
  await flush();

  assert(
    document.getElementById('total').textContent === String(agents.length),
    'Fleet did not load'
  );

  requests.length = 0;
}

async function run(name, fn) {
  try {
    await fn();
    results.push({name, status: 'PASS'});
  } catch (error) {
    results.push({
      name,
      status: 'FAIL',
      detail: String(error && error.message || error)
    });
  }
}

(async () => {

  await run('Clear access invalidates pending inventory response', async () => {
    reset();
    click('refresh');

    assert(requests.length === 1, 'Refresh was not initiated');

    click('clear');
    requests[0].resolve(response([agent()]));
    await flush();

    assert(
      document.getElementById('fleet').children.length === 0,
      'Old response repopulated fleet after clear'
    );
    assert(
      document.getElementById('total').textContent === '—',
      'Old response restored fleet totals'
    );
    assert(
      document.getElementById('message').textContent === 'Access cleared.',
      'Old response overwrote access-cleared message'
    );
  });

  await run('Older refresh cannot overwrite newer refresh', async () => {
    reset();
    click('refresh');
    click('refresh');

    assert(requests.length === 2, 'Expected two inventory requests');

    requests[1].resolve(response([agent('approved')]));
    await flush();

    requests[0].resolve(response([]));
    await flush();

    assert(
      document.getElementById('total').textContent === '1',
      'Older response replaced newer fleet'
    );
    assert(
      document.getElementById('approved').textContent === '1',
      'Older response replaced newer approval status'
    );
  });

  await run('Cancelled revocation never submits POST', async () => {
    reset();
    await loadFleet([agent('approved')]);

    window.prompt = () => null;

    const revoke = [...document.querySelectorAll('button')]
      .find(button => button.textContent === 'Revoke identity');

    assert(revoke, 'Revoke button not rendered');
    revoke.click();
    await flush();

    assert(requests.length === 0, 'Cancelled revocation submitted request');
    assert(
      document.getElementById('message').textContent === 'Revocation cancelled.',
      'Cancellation message missing'
    );
  });

  await run('Revocation requires exact confirmation', async () => {
    reset();
    await loadFleet([agent('approved')]);

    window.prompt = () => 'revoke';

    const revoke = [...document.querySelectorAll('button')]
      .find(button => button.textContent === 'Revoke identity');

    revoke.click();
    await flush();

    assert(
      requests.length === 0,
      'Incorrect confirmation submitted revocation'
    );
  });

  await run('Uncertain mutation blocks another action until refresh', async () => {
    reset();
    await loadFleet([agent('pending')]);

    window.confirm = () => true;

    const approve = [...document.querySelectorAll('button')]
      .find(button => button.textContent === 'Approve agent');

    assert(approve, 'Approve button not rendered');
    approve.click();

    assert(requests.length === 1, 'Approval POST was not submitted');
    assert(requests[0].options.method === 'POST', 'Expected POST request');
    assert(
      requests[0].url.endsWith('/test-agent-001/approve'),
      'Unexpected approval endpoint'
    );

    requests[0].reject(new TypeError('Simulated connection loss'));
    await flush();

    assert(
      document.getElementById('message').textContent.includes('uncertain'),
      'Uncertain outcome warning missing'
    );
    assert(
      document.getElementById('fleet').children.length === 0,
      'Untrusted inventory remained displayed'
    );

    requests.length = 0;
    click('refresh');

    assert(
      requests.length === 1 &&
      requests[0].url === '/api/v1/admin/agents',
      'Recovery did not require fresh inventory'
    );

    requests[0].resolve(response([agent('approved')]));
    await flush();

    assert(
      document.getElementById('approved').textContent === '1',
      'Recovery did not display authoritative status'
    );
  });

  await run('Refresh cannot overlap lifecycle mutation', async () => {
    reset();
    await loadFleet([agent('pending')]);

    const approve = [...document.querySelectorAll('button')]
      .find(button => button.textContent === 'Approve agent');

    approve.click();

    assert(requests.length === 1, 'Approval request missing');

    click('refresh');

    assert(
      requests.length === 1,
      'Refresh started while lifecycle mutation was pending'
    );

    requests[0].resolve({ok: true, status: 200});
    await flush();

    assert(
      requests.length === 2,
      'Successful mutation did not request fresh inventory'
    );

    requests[1].resolve(response([agent('approved')]));
    await flush();

    assert(
      document.getElementById('approved').textContent === '1',
      'Lifecycle refresh did not update status'
    );
  });

  await run('Clear during mutation prevents stale UI restoration', async () => {
    reset();
    await loadFleet([agent('pending')]);

    const approve = [...document.querySelectorAll('button')]
      .find(button => button.textContent === 'Approve agent');

    approve.click();

    assert(requests.length === 1, 'Approval request missing');

    click('clear');
    requests[0].resolve({ok: true, status: 200});
    await flush();

    assert(
      document.getElementById('total').textContent === '—',
      'Mutation response restored cleared totals'
    );
    assert(
      document.getElementById('message').textContent === 'Access cleared.',
      'Mutation response overwrote clear message'
    );
    assert(
      requests.length === 1,
      'Cleared mutation initiated another authenticated request'
    );
  });

  const passed = results.filter(result => result.status === 'PASS').length;
  const failed = results.length - passed;

  output.textContent = JSON.stringify({
    completed: true,
    passed,
    failed,
    results
  });

})().catch(error => {
  output.textContent = JSON.stringify({
    completed: true,
    passed: 0,
    failed: 1,
    results: [{
      name: 'Test harness',
      status: 'FAIL',
      detail: String(error)
    }]
  });
});
"""


class DashboardBrowserBehaviorTests(unittest.TestCase):

    def test_actual_dashboard_javascript_in_chromium(self):
        chromium = shutil.which("chromium")
        if not chromium:
            self.skipTest("Chromium not installed")

        self.assertIn("<script>", PAGE)
        self.assertIn("</body>", PAGE)

        # Insert the test harness after the real dashboard script.
        # All network calls are intercepted before any user interaction.
        html = PAGE.replace(
            "</body>",
            "<script>\n" + BROWSER_TESTS + "\n</script></body>",
            1,
        )

        with tempfile.TemporaryDirectory(
            prefix="versionary-browser-tests-"
        ) as directory:
            root = Path(directory)
            page = root / "dashboard-test.html"
            page.write_text(html, encoding="utf-8")

            command = [
                chromium,
                "--headless",
                "--disable-gpu",
                "--no-first-run",
                "--no-default-browser-check",
                "--disable-background-networking",
                "--disable-extensions",
                f"--user-data-dir={root / 'profile'}",
                "--virtual-time-budget=5000",
                "--dump-dom",
                page.as_uri(),
            ]

            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=35,
                check=False,
            )

            import re
            match = re.search(
                r'<pre id="browser-test-results">(.*?)</pre>',
                completed.stdout,
                flags=re.DOTALL,
            )

            self.assertIsNotNone(
                match,
                "Chromium did not produce test results.\n"
                + completed.stderr[-2000:],
            )

            import html as html_module
            result = json.loads(html_module.unescape(match.group(1)))

            self.assertTrue(result["completed"])

            for item in result["results"]:
                print(
                    f"[{item['status']}] {item['name']}"
                    + (
                        f": {item.get('detail', '')}"
                        if item["status"] == "FAIL"
                        else ""
                    )
                )

            self.assertEqual(
                result["failed"],
                0,
                f"Browser behavioral failures: {result['results']}",
            )
            self.assertEqual(result["passed"], 7)


if __name__ == "__main__":
    unittest.main()
