const assert = require('node:assert/strict');
const { spawn } = require('node:child_process');
const { once } = require('node:events');
const path = require('node:path');
const test = require('node:test');
const { WebSocketServer } = require('ws');

for (const mode of ['percent', 'value']) {
  for (const outcome of ['success', 'success-false', 'error-true']) {
    test(`set-node-progress ${mode}: ${outcome}`, { timeout: 10000 }, async (t) => {
      const server = new WebSocketServer({ host: '127.0.0.1', port: 0 });
      await once(server, 'listening');
      t.after(() => new Promise((resolve) => {
        for (const socket of server.clients) socket.terminate();
        server.close(resolve);
      }));
      const result = {
        success: outcome !== 'success-false',
        ...(outcome === 'error-true' ? { error: true } : {}),
        range: { min: 0, max: 100 },
      };
      const requests = [];
      server.on('connection', (socket) => socket.on('message', (data) => {
        const request = JSON.parse(data.toString());
        requests.push(request);
        socket.send(JSON.stringify({ id: request.id, ok: true, result }));
      }));
      const args = ['act', 'set-node-progress', '-d', '0', '-i', '1'];
      args.push(...(mode === 'percent'
        ? ['--percent', '25']
        : ['--value', '25', '--range-min', '0', '--range-max', '100']));
      const child = spawn(process.execPath, [
        path.join(__dirname, '..', 'dist', 'aohp.js'),
        '--url', `ws://127.0.0.1:${server.address().port}`, ...args,
      ], { stdio: ['ignore', 'pipe', 'pipe'] });
      t.after(() => { if (child.exitCode === null) child.kill(); });
      let stdout = '', stderr = '';
      child.stdout.on('data', (chunk) => { stdout += chunk; });
      child.stderr.on('data', (chunk) => { stderr += chunk; });
      const [code] = await once(child, 'close');
      assert.equal(requests.length, 1);
      assert.equal(requests[0].method, 'act.set_node_progress');
      assert.equal(requests[0].params.percent, 25);
      if (outcome === 'success') {
        assert.equal(code, 0, stderr);
        assert.equal(stderr, '');
        assert.equal(JSON.parse(stdout).success, true);
        if (mode === 'value') assert.equal(JSON.parse(stdout).requestedValue, 25);
      } else {
        assert.equal(code, 2, `failed action must fail the CLI; stdout=${stdout}`);
        assert.equal(stdout, '');
        assert.deepEqual(JSON.parse(stderr), result);
      }
    });
  }
}
