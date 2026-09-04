# AgentReel

One command turns a [Solari](https://getsolari.com) browser agent into a shareable WebM + GIF demo — and patches it into your README.

```bash
agentreel run my_agent.py
```

```text
▶ Running agent...
✓ Agent completed
▶ Waiting for recording...
✓ Recording available
▶ Converting recording...
✓ WebM generated
✓ GIF generated
▶ Updating README...
✓ README updated
▶ Committing changes...
✓ Commit created
```

## Installation

```bash
pip install -e .
# system deps
npm install -g rrvideo   # requires Node.js; pulls Playwright browsers on install
# ffmpeg and git must be on PATH
```

Check your environment:

```bash
agentreel doctor
```

### Requirements

| Dependency | Purpose |
| --- | --- |
| Python 3.10+ | AgentReel CLI |
| `solari-browser` | Launch recorded Solari sessions |
| Node.js + `rrvideo` | rrweb events → WebM |
| `ffmpeg` | WebM → GIF |
| Git | Auto-commit demos (optional with `--no-git`) |

## Quick start

1. Swap your Solari session creation for `recorded_session()`:

```python
import asyncio
from agentreel import recorded_session

async def main():
    async with recorded_session() as browser:
        page = await browser.new_page()
        await page.goto("https://example.com")
        print(await page.title())

asyncio.run(main())
```

`recorded_session()` always sets `recording=True`. Recording is **opt-in per session** in Solari — a session created without it will 404 on the replay endpoint forever.

2. Run:

```bash
export SOLARI_API_KEY=slr_live_...
agentreel run my_agent.py
```

## How it works

```text
agent script (subprocess)
    → recorded_session()  # Solari launch(recording=True)
    → browser.close()     # release triggers async upload
    → poll download_replay(session_id)  # default 20 × 3s
    → events.ndjson + events.json
    → rrvideo → demo.webm
    → ffmpeg  → demo.gif
    → README "Watch it work" section
    → git add (AgentReel files only) + commit
```

The CLI and agent communicate via a temp metadata file (`AGENTREEL_META_PATH`) — not fragile stdout parsing.

## Output layout

```text
reel/
  my-agent-20260904-123000/
    events.ndjson        # raw Solari replay (NDJSON)
    events.json          # JSON array for rrvideo
    demo.webm
    demo.gif
    agentreel-meta.json
```

## CLI

```bash
agentreel run my_agent.py
agentreel run my_agent.py --name my-demo
agentreel run my_agent.py --output ./reel
agentreel run my_agent.py --retries 20 --interval 3
agentreel run my_agent.py --gif-fps 10 --gif-width 800
agentreel run my_agent.py --no-git
agentreel run my_agent.py --no-readme
agentreel run my_agent.py --verbose
agentreel run my_agent.py --debug

agentreel convert path/to/events.json -o ./out
agentreel doctor
```

## README integration

AgentReel inserts an idempotent block:

```markdown
<!-- agentreel:start -->
## Watch it work

![Agent demo](reel/<demo-name>/demo.gif)
<!-- agentreel:end -->
```

Re-runs update the GIF path instead of duplicating the section. Only AgentReel-generated files (plus the README when patched) are staged — never `git add .`.

## Troubleshooting

| Symptom | Fix |
| --- | --- |
| `Recording was not available after N attempts` | Confirm `recorded_session()` / `recording=True`. Retry with `--retries 40 --interval 5`. Upload is async after session release; the first polls often 404. |
| `rrvideo not found` | `npm install -g rrvideo` |
| `ffmpeg not found` | Install ffmpeg and ensure it is on PATH |
| Agent completed but no session metadata | Script must use `from agentreel import recorded_session` |
| Flickering / bad WebM | AgentReel retries a normalized events file; keep `events.json` as the lossless source |

Keep demos short — rrweb event files can exceed 100MB on long sessions.

## Development

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

## Cookbook examples

This repository also includes the original [Solari cookbook](examples/) examples under `examples/` (browser, sandbox, desktop). The AgentReel demo agent lives at `examples/agentreel-demo/main.py`.

## License

MIT
