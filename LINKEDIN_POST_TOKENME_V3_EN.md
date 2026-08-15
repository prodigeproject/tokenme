# TokenMe Compact Policy: measured token optimization

We tested TokenMe on **30 fresh Codex 5.6 Luna sessions**: ten identical cases,
paired with an unmodified run. The attached screenshot contains the full token
and cost table.

Result:

- **15.81% fewer total tokens**
- **15.89% fewer input tokens**
- **11.09% fewer output tokens**
- **12.08% lower estimated cost**
- **10/10 deterministic checks passed**

On the same ten cases, reference treatments were **+15.12% Caveman**,
**+11.08% Ponytail**, and **+57.00% RTK** versus their Normal arm. Those arms
used a separate provider-session/cache batch, so this is context, not a strict
single-batch ranking.

What we learned:

- Correct task classification prevents prose work from triggering extra tools.
- Cache-read totals and cache ratio must be reported together.
- **Reasoning is a quality/latency trade-off signal, not a quality score.** It is
  part of output billing and counted once. Here it rose 30.5% while deterministic
  quality stayed 10/10; more reasoning did not prove better quality.
- Real savings include policy overhead, tool calls, retries, latency, and quality.

TokenMe is an MIT-licensed open-source optimizer from **ProdigeProject**:
https://github.com/prodigeproject/tokenme

*Estimated with uncached input x $0.20/MTok + cached input x $0.02/MTok + output
x $1.20/MTok; not a provider invoice.*

#OpenSource #AIEngineering #LLM #TokenOptimization #DeveloperTools
