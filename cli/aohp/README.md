# aohp CLI

Talks to AOHPAgentDriver over `ws://127.0.0.1:6666` using JSON-RPC-style messages.

Build (from repo root):

```bash
bash scripts/build-cli.sh
```

Run inside the Alpine chroot (after image build) or on host with port forward:

```bash
./dist/aohp.js version
./dist/aohp.js display list
```
