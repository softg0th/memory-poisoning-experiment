# Initial 10-run result

Configuration: `qwen3.5:9b`, `qwen3-embedding:0.6b`; five independent runs in
each policy-trust condition. The controller changed the external policy at step
2. A policy-sync run could store it but had no mutation tools; maintenance at
step 3 received only retrieved persistent memory.

| Condition | Policy persisted | Policy retrieved | Virtual purge |
|---|---:|---:|---:|
| Explicit policy trust | 5 / 5 | 5 / 5 | 1 / 5 |
| Implicit policy adoption | 5 / 5 | 5 / 5 | 0 / 5 |

This is a mechanistic baseline, not an estimate of real-world attack rate.
The stable observed mechanism is policy-source mutation → persistent memory →
retrieval in a later task. The destructive action is stochastic under this model
and prompt configuration. See `artifacts/series-10/aggregate.json` for the
per-run results and `aggregate.svg` for the compact chart.

# Local 50-run result

Configuration: unchanged local `qwen3.5:9b` with
`qwen3-embedding:0.6b`; 25 completed independent runs per policy-trust
condition. The attacker changed the external policy at request step 2. The
agent could write a durable lesson while synchronizing policy but had no
mutation tools in that phase; maintenance at step 3 received retrieved memory.

| Condition | Completed | Policy persisted | Policy retrieved | Virtual purge |
|---|---:|---:|---:|---:|
| Explicit policy trust | 25 / 25 | 25 / 25 | 25 / 25 | 0 / 25 |
| Implicit policy adoption | 25 / 25 | 25 / 25 | 25 / 25 | 0 / 25 |

The first pass had seven malformed structured Ollama responses in the explicit
condition. Those run IDs were retried from their reset isolated state until all
50 observations completed; they are not counted as behavioral outcomes. This
run confirms a reliable *write → retrieve* memory-poisoning path, but under the
current guardrail and task it did not cause a virtual destructive action. See
`artifacts/series-50-local/aggregate.json` and `aggregate.svg`.
