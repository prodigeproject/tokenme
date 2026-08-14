# Audit: TokenMe vs Caveman on Codex 5.6 Luna

> **Archived run.** This report describes the earlier router-v3, three-arm
> audit. The newest same-case v2/v3 head-to-head is the 60-cell
> [`LATEST_6_ARM_REPORT.md`](LATEST_6_ARM_REPORT.md); use that report for
> current public numbers. Older transition artifacts remain local and are not
> part of the public source snapshot.

Tanggal run lokal: 15 Agustus 2026. Repo yang diaudit: `C:\Users\Pc\Downloads\tokenme`. Repo Caveman: `C:\Users\Pc\Downloads\caveman-main`.

## Kesimpulan singkat

TokenMe dan Tokenisme bukan produk yang sama:

- **TokenMe** adalah optimizer open-source/policy/measurement layer. Ia memilih policy prompt, memberi quality signal, dan membaca telemetry provider. Ia bukan gateway transparan, cache controller, compressor request, atau pemilik billing.
- **Tokenisme** adalah gateway/marketplace inference bisnis. Ia tempat yang tepat untuk credentials, routing provider, price book, reservations, cache settlement, CCR storage/recovery, retry, dan enforcement reasoning budget.

Pada benchmark baru yang benar-benar memanggil Codex 5.6 Luna, TokenMe mengurangi provider-reported total token dibanding Normal pada task pack ini, sedangkan Caveman **skill** meningkat. Hasil ini tidak berarti TokenMe menang universal; interval paired dan satu sesi per case masih kompatibel dengan noise. Temuan paling penting adalah output TokenMe turun, tetapi reasoning component naik—jadi optimasi output harus mengejar total cost dan kualitas, bukan sekadar memendekkan teks.

## 1. Apa yang dibandingkan

Benchmark terdiri dari 10 kasus identik, masing-masing dijalankan sebagai sesi `codex exec --ephemeral` baru untuk tiga arm (30 sesi):

| Stratum | Kasus | Tujuan |
|---|---:|---|
| prose/safety | 4 | laporan 350–500 kata, kontrak API, arsitektur, security facts |
| Bash/RTK-heavy | 3 | output command repetitif, error filtering, route counting |
| over-building/Ponytail-heavy | 3 | reuse helper, fungsi kecil, larangan dependency/abstraction baru |

Arm Normal tidak menerima policy tambahan. Arm Caveman menerima teks persis dari `C:\Users\Pc\Downloads\caveman-main\plugins\caveman\skills\caveman\SKILL.md`. Arm TokenMe memakai `tokenme.router.route_text()` lalu `tokenme.prompt.render_instructions()`.

Setiap cell menyimpan prompt, raw JSONL, stderr, final response, copied workspace, `result.json`, dan deterministic score. Tidak ada API key provider yang dipasang; Codex CLI/session lokal dipakai untuk menghasilkan telemetry `turn.completed`.

### Ledger yang dipakai

`total_tokens = input_tokens + output_tokens`.

`cached_input_tokens`, `cache_write_input_tokens`, dan `reasoning_output_tokens` adalah komponen provider; tidak ditambahkan lagi. `fresh_input = (input - cache_read) + cache_write`. Cache-read bukan bukti bahwa optimizer tertentu menyebabkan cache hit. Biaya di bawah adalah price-sheet estimate, bukan invoice lokal.

## 2. Hasil live provider telemetry

| Arm | Sesi lengkap | Input | Cache read | Cache write | Fresh input | Reasoning | Output | Total | Quality predicate | Estimasi Luna* |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Normal | 10/10 | 800,664 | 644,352 | 0 | 156,312 | 1,998 | 13,463 | 814,127 | 10/10 | $0.060305 |
| Caveman skill | 10/10 | 913,062 | 741,376 | 0 | 171,686 | 2,158 | 12,510 | 925,572 | 10/10 | $0.064177 |
| TokenMe | 10/10 | 744,249 | 591,872 | 0 | 152,377 | 2,314 | 11,928 | 756,177 | 10/10 | $0.056626 |

`*` Formula: uncached input × $0.20/MTok + cache-read × $0.02/MTok + cache-write × $0.25/MTok + output × $1.20/MTok. Harga diambil dari [halaman resmi GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna); sesi Codex lokal ini bukan API invoice.

Perubahan terhadap Normal (positif berarti lebih rendah):

- **TokenMe:** total −7.12%, input −7.05%, fresh input −2.52%, output −11.40%, estimasi cost −6.10%.
- **Caveman skill:** total **+13.69% lebih tinggi**, input +14.04%, fresh input +9.84%, output −7.08%, estimasi cost +6.42% lebih tinggi.
- Reasoning output TokenMe naik 15.82% (2,314 vs 1,998). Ia tidak boleh dianggap sebagai saving tambahan; reasoning sudah berada di dalam output provider.

Tool-output chars turun (Normal 73,824; Caveman 57,736; TokenMe 51,873), tetapi jumlah `item.completed` command naik (Normal 28; Caveman 32; TokenMe 33). Ini menjelaskan mengapa kompresi/ketelitian output lokal tidak otomatis menjadi penghematan bill: extra turn, re-read, dan hidden/system context tetap dominan.

Ada transient tool-router errors di stderr yang tidak menggagalkan final predicate: Normal 5 event pada 3 cell, Caveman 5 pada 4 cell, TokenMe 2 pada 2 cell. Runner saat ini menilai workspace/final result, bukan retry/error tax; angka ini harus masuk ke net-saving metric berikutnya.

Paired bootstrap dari runner:

- TokenMe total delta mean −5,795 token, tetapi median +257.5 dan 95% CI mean [−29,155, +14,851]. Jadi aggregate −7.12% adalah hasil task pack, bukan bukti universal.
- TokenMe output delta mean −153.5 token; 95% CI [−290, −15] pada pack ini.
- Price-sheet cost delta CI juga melintasi nol.

## 3. Pola per task dan diagnosis

TokenMe menang total pada `prose_release` (−61.61%), `pony_strip_version` (−28.03%), `rtk_errors` (−20.87%), dan `rtk_redact` (−20.18%). Ia kalah pada `prose_api` (+141.66%), `pony_csv_column` (+46.67%), `prose_arch` (+27.27%), `pony_dedupe` (+1.88%), `rtk_routes` (+0.32%), dan `prose_security` (+0.44%).

Regresi paling jelas adalah `prose_api`: router TokenMe membaca kata “api” sebagai sinyal code dan menambahkan layer code/tool policy. Sesi TokenMe melakukan 5 shell calls dan berakhir 92,461 token, dibanding Normal 2 shell calls dan 38,261 token. Ini bukan kegagalan model memahami API; ini kegagalan **route economics**. Kata “run one focused check” juga memicu layer tools pada helper tasks yang sebenarnya tidak memerlukan command-output compression.

**Post-benchmark fix:** `tokenme/router.py` sekarang v4 mengenali read-only prose deliverables (final report, fixed headings, `do not modify`) dan menekan layer code/tool kecuali ada implementation verb atau noisy-output signal. Regression tests memastikan `prose_api` dan `prose_security` menjadi `[layer1-prose]`, sementara implementation/RTK tasks tetap mendapat layer yang diperlukan. Angka 10-case di atas adalah hasil router v3 sebelum fix ini; belum diklaim sebagai hasil rerun v4.

Per stratum:

| Stratum | Normal | Caveman | TokenMe |
|---|---:|---:|---:|
| Bash/RTK-heavy | 329,264 | 330,007 | **280,673 (−14.76%)** |
| prose/Caveman | 273,939 | 270,948 | **259,523 (−5.26%)** |
| overbuild/Ponytail | 210,924 | 324,617 | 215,981 (+2.40%) |

## 4. JetBrains claims vs audit kita

Riset JetBrains mengukur tool pada model, harness, dan counter yang berbeda. Karena itu angka tidak boleh dicampur sebagai satu leaderboard.

1. [Caveman: “Does Speaking to Agents Like Cavemen Really Save 65%?”](https://blog.jetbrains.com/ai/2026/07/speak-to-ai-agents-like-cavemen-tosave-tokens/) memisahkan klaim iklan 65% dari paired Claude Code benchmark: forced activation menghasilkan sekitar 8.5% output-token saving pada 82 task, tanpa quality degradation yang terdeteksi. JetBrains juga menunjukkan cost total dapat terbalik karena satu long-context outlier. Audit Luna kita melihat Caveman skill output −7.08% tetapi total +13.69% karena policy panjang dan perilaku sesi.
2. [RTK: “Does rtk skill really cut agent tokens by 60–90%?”](https://blog.jetbrains.com/ai/2026/07/rtk-claude-code-token-savings/) menemukan +7.6% median cost pada low effort dan sekitar 0% pada high effort, sambil menunjukkan scoreboard RTK menghitung counterfactual chars/4 dan raw output yang sebagian sudah dipotong host. Audit kita **tidak menjalankan RTK binary sebagai arm**; kasus Bash/RTK-heavy hanya dipakai sebagai stress stratum untuk Normal/Caveman/TokenMe. Jadi tidak ada klaim RTK-vs-TokenMe baru dari run ini.
3. [Ponytail: “Does It Really Cut Agent Code by 54%?”](https://blog.jetbrains.com/ai/2026/07/ponytail-skill-claude-tested/) melaporkan −15% code dan −10.3% cost pada 80 paired task, dengan efek terkonsentrasi pada task yang memang over-build. Audit kita **tidak menjalankan Ponytail sebagai arm**; tiga kasus over-build hanya menguji apakah policy TokenMe/Normal/Caveman ikut menghasilkan pola yang sama. Karena itu angka Ponytail yang sah di sini adalah angka JetBrains, bukan hasil re-run kita.

Hal yang metodologinya sama dan benar: paired cases, model/settings dipin, quality verifier, raw/provider accounting, dan per-task comparison. Hal yang lebih lemah di run kita: satu sesi per case (bukan k=3/k=5), task pack sengaja kecil dan mekanistik, temp workspace path berbeda antar batch, dan beberapa batch runner sebelumnya sempat mengisi artifact secara serial. Semua 30 cell akhirnya lengkap dan 10/10 predicate per arm, tetapi variance dan batch timing tetap dicatat sebagai keterbatasan.

`10/10` di sini berarti predicate fixture/fungsi dan marker laporan terpenuhi, bukan semantic equivalence atau human readability. `added_loc` mechanism scorer juga tidak diff-aware (menghitung code pada copied workspace), sehingga tidak dipakai sebagai bukti minimality/anti-overbuilding; checker Ponytail/RTK hanya memanggil target function.

## 5. Deep audit arsitektur

| Dimensi | TokenMe saat ini | Caveman skill/proxy | Keputusan untuk TokenMe |
|---|---|---|---|
| Token optimization | Router regex + compiled instruction; tidak mengubah request/response payload | Skill memendekkan narration; proxy punya typed compressors/provider adapters | Bangun policy/contract provider-neutral; compressor sebagai plugin, bukan asumsi core |
| Provider tokenizer | Optional `tiktoken`, fallback `~est`; Luna tidak punya tokenizer exact di env | Embedded BPE; provider endpoint bila tersedia; menandai inferred/verified | Bangun adapter interface; `chars/4` tidak boleh menjadi billing truth |
| Cache | Parser hanya membaca cache fields; tidak mengontrol cache key/TTL | Prefix cache planning, affinity, provider-native counters | Planner/interface di TokenMe; controller/settlement di Tokenisme |
| Context packing | Layer4 audit/checkpoint text-only; tidak ada session context manager | Context IR, live/frozen zones, compaction, relevance retrieval | Lossless metadata/packer di TokenMe; session state dan policy enforcement di Tokenisme |
| Recovery | Tidak punya CCR | Content-addressed exact recovery, SQLite/WAL, fail-closed S4 | Expose `RecoveryStore` protocol; durable encrypted storage di gateway |
| Routing | Regex route + local feedback; tidak memakai provider price/latency/net benefit | Provider/model/effort candidate routing dengan quality/cost/latency evidence | TokenMe memberi advisory route/simulation; Tokenisme melakukan dispatch |
| Reasoning | Prompt hanya memberi gaya/safety; tidak enforce budget | Provider adapter dapat memilih effort dengan eval gates | TokenMe keluarkan `BudgetHint`; Tokenisme enforce/reserve/settle |
| Economics | Tidak ada price catalog; `provider_cost` hanyalah metric type | Raw usage, price eligibility, cache/reasoning subset, complete/partial/malformed | Telemetry contract di TokenMe; price book dan billing di Tokenisme |
| Quality | Heuristic diff/security/accessibility signals | Fail-closed transforms, CCR/round-trip gates, external graders | Tambah host callback/round-trip contract; jangan klaim semantic proof dari regex |
| Latency/failure | Local stdlib ringan; tracker/feedback lock belum kuat; no retry/recovery model | Proxy adds compression/CCR/DB/adapter overhead, with original-byte fallback | Record latency, retries, tool errors, recovery attempts; keep core local |
| Operasional/lisensi | MIT, stdlib, mudah dipasang sebagai library/skill | Skill/CLI surfaces MIT; Go engine/proxy/CCR BSL-1.1 | Clean-room protocol/integration; jangan copy BSL engine ke TokenMe |

Evidence TokenMe: `tokenme/router.py`, `prompt.py`, `provider.py`, `tracker.py`, `quality.py`, `layer4.py`, `estimate.py`, dan `cli.py`. Evidence Caveman: `engine/engine.go`, `engine/ccr/*`, `engine/compressors/*`, `proxy/providers/*`, `proxy/internal/gateway/*`, `cacheengine/*`, `packages/agent/src/context-ir.ts`, `compaction.ts`, dan `budget.ts`.

## 6. Prioritas peningkatan TokenMe (tetap open-source optimizer)

### P0 — route yang sadar net benefit

Tambahkan mode eksplisit `prose/report/read-only` dan bedakan “run one check” dari “large command output”. Sebelum menambah layer policy, lakukan `simulate()`:

```text
expected provider saving
− policy prompt overhead
− extra tool/turn overhead
− retry/recovery overhead
− latency cost
```

Jika hasil tidak positif atau confidence rendah, kirim core policy saja. Ini langsung menutup regresi `prose_api` dan menghindari false-positive `security`/`api`/`run`.

### P0 — telemetry provider-neutral yang benar

Evolusi `provider.py` menjadi schema yang membawa provider/model, token basis (`provider`, `inferred`, `unknown`), input/cache-read/cache-write/reasoning/output, latency/TTFB, retries, tool errors, recovery attempts, dan quality callback. Simpan raw events; jangan silent-zero field yang tidak dilaporkan. Price table harus injectable, bukan hardcoded sebagai klaim universal.

### P0 — tokenizer adapter, bukan chars/4

Expose interface `count(text, provider, model, mode)` dengan `method`, `confidence`, dan `scope`. Provider count endpoint menjadi authoritative bila tersedia; BPE lokal hanya `inferred`. Hidden system/tool framing tetap `unknown`.

### P1 — output optimization yang aman

Target output karena rate output lebih tinggi, tetapi jangan memotong reasoning/quality secara buta. Gunakan summary policy adaptif: brief hanya saat task selesai dan no safety ambiguity; expanded untuk security, failure, validation, accessibility, or unresolved state. Track `output_tokens`, `reasoning_output_tokens`, quality, and extra turns separately.

### P1 — lossless context packer + optional compressor ABI

Tambahkan segment metadata: kind, stability, priority, relevance, recency, error/security pin, cache region, provenance, and recovery handle. Default transform harus lossless/byte-stable. Lossy compressor hanya plugin dengan round-trip/quality gate, explicit `lossiness`, and fail-closed fallback.

### P2 — protocol, not gateway duplication

TokenMe boleh mendefinisikan `RecoveryStore`, `BudgetHint`, `ProviderTokenizer`, `QualityEvaluator`, dan `NetBenefitReport` protocols. Tokenisme yang mengimplementasikan durable CCR, provider-specific cache, price settlement, reservation, routing, quota, and reasoning enforcement.

## 7. Build vs integrate decision

**Build in TokenMe:** classification/eligibility, adaptive prompt policy, tokenizer adapter contract, lossless context metadata/packer, simulation/net-benefit math, raw-vs-inferred ledger, quality/round-trip interfaces, and optional recovery/budget protocols.

**Integrate in Tokenisme:** provider credentials/adapters, exact count endpoints, price and cache settlement, cross-provider routing, reservations, latency/error SLO, durable encrypted CCR, recovery/retry, and enforcement of reasoning/output budgets.

**Do not copy:** Caveman BSL engine/proxy/CCR implementation into the MIT TokenMe core. Use clean-room interfaces and optional integrations. The open-source optimizer should remain portable and useful even when no gateway is present.

## 8. Reproduction and artifacts

```powershell
python benchmark/audit_10_case/run_luna.py `
  --codex C:\Users\Pc\AppData\Local\Temp\tokenme-codex-cli.exe `
  --model gpt-5.6-luna --reasoning-effort low `
  --tasks benchmark/audit_10_case/tasks.py `
  --score benchmark/provider_total/mechanism_score.py `
  --result-root benchmark/audit_10_case/runs_luna

python benchmark/audit_10_case/analyze.py
```

Raw JSONL and per-cell artifacts are under `benchmark/audit_10_case/runs_luna/`. The compact derived files are `RESULTS.json`, `RESULTS.md`, `AUDIT_SUMMARY.json`, and `AUDIT_SUMMARY.md`. The runner and analyzer are `run_luna.py`, `tasks.py`, and `analyze.py`.

No TokenMe product/source file was modified for this audit. The only new code is benchmark harness/analyzer documentation.
