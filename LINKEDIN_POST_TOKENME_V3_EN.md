# TokenMe Compact Policy: measured token optimization

Token-saving claims are easy to make from prompt length. We wanted a result
measured from provider usage on identical coding-agent work.

In the latest 30-cell Codex 5.6 Luna run, ten identical cases were paired
between an unmodified run and TokenMe's Compact Policy. Every deterministic
fixture check passed.

The attached benchmark screenshot shows the complete input, cache-read,
reasoning, output, total-token, and estimated-cost table. The headline result:

- **15.81% fewer total tokens**
- **15.89% fewer input tokens**
- **11.09% fewer output tokens**
- **12.08% lower estimated cost**
- **10/10 deterministic quality checks**

Reasoning increased 30.5% in this task pack, so it is reported separately rather
than presented as a saving. Reasoning is a subset of output and is counted once
in the cost formula.

For the same ten cases, the reference treatment run recorded Caveman at
**+15.12%**, Ponytail at **+11.08%**, and RTK at **+57.00%** versus that run's
Normal arm. Those reference arms came from a separate provider-session/cache
batch, so the comparison is context, not a claim of identical cache conditions.

What we learned from the Compact Policy:

- **Classification is an optimization boundary.** A prose task accidentally
  routed as code/tool work can trigger extra commands and erase the saving.
  Explicit task modes and a stop-after-sufficient-check rule matter.
- **Cache-read is not cache efficiency.** A smaller request can have fewer
  absolute cache-read tokens while keeping a healthy cache ratio, so both must
  be reported.
- **Prompt policy cannot enforce reasoning budgets.** Reasoning is provider
  output; controlling it needs a provider or gateway adapter, and it must never
  be double-counted.
- **Net savings cover the whole trajectory.** Policy length, tool calls, retries,
  recovery, latency, and quality belong in the measurement - not just final
  answer length.

TokenMe is an MIT-licensed open-source optimizer from **ProdigeProject**.
Explore the code and methodology:

https://github.com/prodigeproject/tokenme

*Estimated with uncached input x $0.20/MTok + cached input x $0.02/MTok + output
x $1.20/MTok; not a provider invoice.*

#OpenSource #AIEngineering #LLM #TokenOptimization #DeveloperTools
