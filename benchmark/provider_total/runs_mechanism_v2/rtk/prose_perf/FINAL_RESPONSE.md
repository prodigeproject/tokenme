Baseline

The report endpoint currently has a p95 latency baseline of 1,240 ms when processing 10,000 records. This is the reference point for evaluating any optimization work. The measurement should remain the comparison baseline because it describes the user-visible tail latency at the workload documented in the fixture, rather than an isolated microbenchmark. Any follow-up result should be gathered under the same workload and operating conditions so the team can make a like-for-like decision. At this stage, the baseline establishes that there is meaningful room to improve response time, but it does not by itself justify changing database access, application behavior, or infrastructure.

Bottleneck

CPU profiling identifies JSON serialization as the bottleneck, accounting for 61% of the measured time. The database query is explicitly not the bottleneck. This distinction should guide engineering effort: database tuning would target the wrong part of the request path and is unlikely to address the dominant cost shown by the profile. The evidence instead points to how application records are converted into the response payload. Because serialization consumes most of the profiled time, an optimization in that stage has a credible path to improving end-to-end p95 latency. However, the profile is diagnostic evidence, not proof that every serializer change will help; implementation overhead and memory behavior still need to be measured.

Experiment

The proposed experiment batches 100 records per serializer call. Its purpose is to test whether reducing per-call overhead improves the report endpoint without creating an unacceptable memory tradeoff. The comparison should use p95 latency as the primary performance measure and memory as the accompanying safety measure, exactly as proposed. Results should be compared with the 1,240 ms baseline at the same 10,000-record workload. This keeps the experiment focused on the identified JSON serialization bottleneck and makes the outcome actionable. A successful result would show a repeatable p95 improvement while memory remains operationally acceptable; a result that improves average behavior but not p95 would not demonstrate progress against the stated baseline. Likewise, any latency gain should be considered alongside memory rather than evaluated in isolation, because batching can change the amount of data retained during processing.

Next action

Run the 100-record batching experiment against the 10,000-record workload, recording p95 latency and memory, and use the 1,240 ms baseline to decide whether to proceed.
