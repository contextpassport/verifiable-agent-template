# Verifiable Agent Template

> The smallest possible setup that gives you a **verifiable record of every decision your AI agent makes**.

Your agent will eventually make a decision someone wants to verify.  Maybe a regulator asks how it reached a conclusion. Maybe a customer disputes an action. Maybe an incident review needs the exact sequence of inputs and outputs that led to a bad outcome.

If that record lives only in your application logs, you are asking the reviewer to trust your logs. For many situations — anything regulated, anything high-stakes, anything where the counterparty might be adversarial — "trust my logs" is not an acceptable answer.

This template wires up a [LangGraph](https://langchain-ai.github.io/langgraph/) agent with [Context Passport](https://contextpassport.com) — an open standard for verifiable AI agent event records. Every step of the agent emits a signed, hash-chained record that anyone can verify without trusting you or any specific vendor.

Clone, install, run. Sixty seconds.

## What you get

After running this template, you have:

1. A working LangGraph agent that researches a topic and produces a short report
2. A complete chain of Context Passports — one per agent step — saved to `./passports/`
3. A verifier that can validate the chain offline with no network access
4. A standalone proof bundle you can hand to anyone (regulator, customer, auditor)

```bash
$ python -m src.agent "What is the EU AI Act Article 12 logging requirement?"
[plan]      -> broke task into 3 sub-questions
[research]  -> searched and analyzed sources
[write]     -> drafted 232-word answer
[verify]    -> integrity chain ok (3 passports, all signatures valid)

Wrote 3 passports to ./passports/
Run `python -m src.verify ./passports/` to verify the chain.
```

## Quick start

```bash
git clone https://github.com/contextpassport/verifiable-agent-template.git
cd verifiable-agent-template
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-...        # required (or use a different provider; see src/agent.py)
python -m src.agent "What is the EU AI Act Article 12 logging requirement?"
python -m src.verify ./passports/
```

That's the whole thing.

## How it works

The template is roughly 200 lines of code across three files:

```
src/
├── agent.py       — the LangGraph agent (plan → research → write)
├── verify.py      — offline chain verifier
└── recorder.py    — wires Context Passport into the agent
```

The integration is one line per step. The `recorder.py` module is a thin wrapper around `context_passport.integrations.langgraph.LangGraphPassportCallback` — drop it into your own LangGraph agent and you have the same property.

## Why this matters

A traditional audit log lives inside the system being audited. If the system can write to it, the system can rewrite it. Regulators, auditors, and counterparties increasingly do not accept this — they want records they can verify without trusting you.

Context Passport gives you that property. Each passport is:

- **Hash-chained** — tampering with any record breaks the chain and is detectable
- **Signed** — records carry an Ed25519 signature tying them to your key; forgery is impossible without the private key
- **Verifiable offline** — the verifier needs only the records and your public key; no DarkMatter, no vendor, no internet
- **Compatible with external timestamping** — anchor checkpoints to OpenTimestamps to defeat backdating

The spec is CC0. The verifier is Apache-2.0. You can run the entire pipeline without depending on any vendor — including the maintainers of this template.

## What the template does NOT do (intentionally)

- **It does not run a Witness Log.** The records sit in `./passports/` on your local disk. For production you would post them to a Context Passport receiving server (hosted or self-hosted) that publishes them to a public, externally-anchored log. See [contextpassport/spec docs/witness-log.md](https://github.com/contextpassport/spec/blob/main/docs/witness-log.md).
- **It does not handle key management.** The template generates a fresh Ed25519 keypair on first run and persists it to `./.keys/`. For production see [contextpassport/spec docs/key-management.md](https://github.com/contextpassport/spec/blob/main/docs/key-management.md).
- **It does not anchor externally.** The records are signed and chained but not anchored to Bitcoin or any external service. To add OpenTimestamps anchoring see [contextpassport/spec docs/external-anchoring.md](https://github.com/contextpassport/spec/blob/main/docs/external-anchoring.md).

The template is the smallest possible viable example. Each of the above is one more step you take when you go to production.

## Extending the template

The agent is a placeholder. The valuable part is the recorder. To use Context Passport in your own LangGraph agent:

```python
from context_passport.integrations.langgraph import LangGraphPassportCallback

handler = LangGraphPassportCallback(
    agent_id="my-agent",
    agent_name="My Agent",
    provider="anthropic",
    model="claude-opus-4-6",
    commit_fn=lambda p: save_to_storage(p),
)

result = my_graph.invoke({"input": ...}, config={"callbacks": [handler]})
```

That's it. Every node execution becomes a chained, signed Context Passport.

## License

This template is released under **Apache-2.0**. Use it, modify it, redistribute it. The Context Passport specification and conformance test suite are CC0.

## Related

- [Context Passport specification](https://github.com/contextpassport/spec) — the open standard
- [Context Passport Python reference implementation](https://github.com/contextpassport/python) — the package this template depends on
- [Context Passport conformance tests](https://github.com/contextpassport/conformance-tests) — the test suite any implementation can run against
- [Context Passport for MCP (draft proposal)](https://github.com/contextpassport/spec/blob/main/proposals/context-passport-for-mcp.md) — verifiable MCP tool invocations

## Contributing

Open a pull request. This template aims to stay small. Improvements that keep it under ~300 lines of agent code and ~100 lines of recorder code are most welcome. Larger additions belong in your own repo, with this template as a starting point.
