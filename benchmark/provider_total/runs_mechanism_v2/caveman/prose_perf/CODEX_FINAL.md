Baseline

Current report endpoint records a p95 latency of 1,240 ms while processing 10,000 records. This measurement provides a clear starting point for evaluating optimization work: any proposed change should be compared against the same workload and percentile, under equivalent test conditions. The baseline is useful because it captures tail latency rather than only an average, making it more representative of slower requests experienced by users. No broader performance conclusion should be drawn until repeated runs confirm that test conditions remain stable.

Bottleneck

CPU profiling identifies JSON serialization as the primary bottleneck, accounting for 61% of execution time. Database query work is not the dominant source of latency. This distinction matters because database tuning, indexing changes, or query rewrites would target the wrong part of the request path and would be unlikely to address most observed processing cost. Optimization effort should focus on how report records are passed to and processed by the serializer. Serialization work may also affect memory pressure, so latency improvements must be assessed alongside memory use rather than treated as a latency-only decision.

Experiment

Proposed experiment batches 100 records per serializer call. For a 10,000-record report, this changes serialization from handling the full result as one undifferentiated operation to processing fixed-size groups. Test should compare p95 latency with the 1,240 ms baseline and track memory at the same time. Multiple comparable runs should be used so normal variability does not masquerade as an improvement or regression. Workload size, data shape, environment, warm-up behavior, and measurement method should remain unchanged between baseline and experimental runs.

Success requires evidence that batching reduces p95 without creating unacceptable memory growth or shifting cost elsewhere in the endpoint. Results should include both latency and memory observations, plus enough run context to reproduce the comparison. If p95 improves but memory usage becomes materially worse, team should treat outcome as a tradeoff requiring review, not an automatic win. If results show no meaningful change, profiling should be repeated around individual serialization calls to determine whether batch setup overhead offsets expected savings.

Next action

Run controlled benchmark using 100-record serializer batches against same 10,000-record workload, record p95 and memory across repeated runs, and compare results directly with 1,240 ms baseline.