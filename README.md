# Context Keeper

**Sessions end. Working memory should not.**

Context Keeper is a Hermes Agent plugin that keeps a rolling checkpoint of the live session and restores it into the next one, so work resumes where it stopped instead of starting over after a restart, a crash, or a context rollover.

Every agent user knows the moment: the session resets and the new instance asks what you were doing. The answer existed, it was just never written down anywhere the next session could read. Context Keeper writes it down continuously, as a mechanism, not as a favour the agent has to remember to do.

## How it works

1. **Rolling trace.** A `post_tool_call` hook records a compact trace while the session works: tool counts, files touched, and recent action hints. Argument values are never stored wholesale, and credential-shaped keys are dropped before anything is written.
2. **Checkpoints.** Every `interval` tool calls (default 10) the trace is written to `$HERMES_HOME/context-keeper/latest.json`, with a bounded history in `checkpoints.jsonl` (default: last 50).
3. **Intentional saves.** The agent can call the `context_save` tool at any moment with a plain-language summary of where the work stands ("gateway fix halfway, tests pending"). That checkpoint becomes the latest and is the one the next session sees first.
4. **Restore.** A `pre_llm_call` hook on the first turn of a new session injects the latest checkpoint as context, clearly labelled as a previous session's record rather than new instructions. It injects once per session, and never into the session that wrote the checkpoint.

## Surfaces

* `/context` in chat: the latest checkpoint, readable at a glance.
* `context_save` tool: save a checkpoint now, with a summary.
* `context_restore` tool: fetch the latest checkpoint on demand.
* `hermes contextkeeper show|history` on the CLI.

## Install

```bash
hermes plugins install Whydiriki700/context-keeper --enable
```

Or copy this directory into `~/.hermes/plugins/context-keeper/` and run `hermes plugins enable context-keeper`, then restart Hermes.

Verify any time with:

```bash
hermes plugins validate ~/.hermes/plugins/context-keeper
hermes plugins doctor ~/.hermes/plugins/context-keeper
```

## Configuration

In `config.yaml`:

```yaml
plugins:
  entries:
    context-keeper:
      settings:
        interval: 10   # tool calls between rolling checkpoints
        keep: 50       # checkpoints retained in history
        inject: true   # restore the latest checkpoint on a new session
        mode: on       # on | off
```

## Honest limitations

* The rolling trace is mechanical: tools, files, action hints. The *meaning* of the work lives in summaries, which is why `context_save` exists; a checkpoint without a summary resumes the facts, not the reasoning.
* One latest checkpoint per Hermes home, not per project. Sessions sharing a home share the checkpoint stream; the session id is recorded on every checkpoint so a restore can be told apart from the live session.
* The restored checkpoint is context, not gospel. It is labelled as a record of earlier work, and the agent is expected to verify before acting on it, the same discipline [ProofGate](https://github.com/Whydiriki700/proofgate) enforces for claims.

## Development

```bash
python3 tests/test_store.py   # 4 scenario tests, no dependencies
```

The store (`store.py`) is pure stdlib with no Hermes imports, so checkpointing and restore formatting can be tested and audited in isolation.

## License

MIT

---

**More by the same author**

- [ProofGate](https://github.com/Whydiriki700/proofgate): no proof, no done. Agent completion claims checked against tool evidence, fail closed.
- [Secret Scan](https://github.com/Whydiriki700/secret-scan): credential patterns redacted from agent replies before delivery, fail closed.
- [Commit Keeper](https://github.com/Whydiriki700/commit-keeper): automatic git checkpoints for agent workspaces, secrets excluded by name.
- [money-magnet](https://github.com/Whydiriki700/money-magnet): finance tracker, budget alerts, crypto portfolio PnL and arbitrage scanner for Hermes Agent.
- [Token Dashboard](https://github.com/Whydiriki700/token-dashboard): live token usage and cost dashboard for Hermes Desktop.
- Osvyn on Telegram: [t.me/osvynofficial](https://t.me/osvynofficial)
