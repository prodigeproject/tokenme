# Before / after — same prompt, measured

Three prompts, answered the default way and with tokenme. Token counts are real,
measured by `tokenme count` (heuristic `~est` shown; install `tiktoken` for exact).
The point isn't only fewer tokens — it's that the shorter version is also clear,
correct, and safe.

Reproduce any row:

```bash
printf '%s' "<text>" | tokenme count -
```

---

## 1. Explanation (Layer 1 — prose)

**Prompt:** "Why does my React component re-render every time I type in a search
box that updates unrelated state?"

**Before — 262 tokens**

> Great question! The reason your component re-renders on every keystroke is that
> the search box is updating a piece of state that lives in (or above) this
> component. In React, whenever you call a state setter, React schedules a
> re-render of the component that owns that state and all of its children,
> regardless of whether they actually use the changed value. So even though the
> rest of your UI doesn't depend on the search text... *(continues for another
> 150 tokens of restatement and options)*

**After (tokenme) — 111 tokens · −58%**

> The search box updates state owned by this component, and any state change
> re-renders the component and all its children, even ones that don't use the
> value. Fix it by moving the search input and its state into their own child
> component, so only that child re-renders. If heavy siblings remain, wrap them in
> `React.memo` and memoize object/callback props with `useMemo`/`useCallback`.
> Colocating the state is usually enough on its own.

Same answer, full sentences, no greeting or repetition. Readable in one pass.

---

## 2. Code (Layer 2 — generated code)

**Prompt:** "Add a date-of-birth field to this HTML signup form."

**Before — 216 tokens:** installs `react-datepicker`, writes a stateful wrapper
component with ten props and a stylesheet import.

**After (tokenme) — 94 tokens · −57%**

```html
<label for="dob">Date of birth</label>
<input type="date" id="dob" name="dob" max="2026-06-19" required>
```

> Used the native date input — no library needed. `max` prevents future dates;
> `required` enforces presence. Add a JS fallback only if you must support browsers
> without `<input type="date">` (now rare).

No dependency, no component, and it **keeps** the validation (`max`, `required`).
Smaller *and* less to maintain — without dropping a safeguard.

---

## 3. Tool output (Layer 3 — input pulled into context)

**Prompt:** "What changed in the repo since the last commit?"

**Before — 3068 tokens:** the full `git diff` dumped into context (120 changed
lines), with the actual answer buried inside it.

**After (tokenme) — 73 tokens · −97.6%**

```
 src/api.py | 240 ++++++++++++++++++++++++------------------
 1 file changed, 120 insertions(+), 120 deletions(-)
(then inspect a single hunk only if needed: git diff -- src/api.py | sed -n '1,30p')
```

`git diff --stat` first answers "what changed" in a fraction of the tokens, and the
drill-down hint means you can still see any hunk on demand — nothing is lost.

---

## Totals

| prompt | before | after | saved |
|--------|-------:|------:|------:|
| 1 prose | 262 | 111 | −58% |
| 2 code | 216 | 94 | −57% |
| 3 tool output | 3068 | 73 | −97.6% |
| **total** | **3546** | **278** | **−92%** |

The largest absolute savings come from tool output (Layer 3) — which is exactly why
tokenme keeps that habit always-on. Run `tokenme report` after a real session to
see your own per-layer breakdown, and `tokenme quality` to confirm no safeguard was
lost along the way.
