Baseline

The report endpoint currently has a baseline latency of 1,240 ms at p95 when processing 10,000 records. This gives the team a concrete reference point for evaluating any optimization: a candidate change should be measured under the same workload and percentile so the comparison remains meaningful. The baseline is high enough to warrant investigation, but it should not be treated as a database problem by default. The available profile separates where the request spends its time and provides a stronger basis for deciding what to optimize first.

Bottleneck

JSON serialization is the bottleneck. CPU profiling attributes 61% of the endpoint's runtime to JSON serialization, not the database query. That concentration indicates that tuning query execution would not address the dominant cost observed in the profile. The optimization effort should therefore focus on how records are passed through the serializer, while preserving the endpoint's response content and behavior. This diagnosis is also useful for review: it ties the proposed change to measured CPU activity rather than to an assumption based on the endpoint's data volume.

Experiment

The proposed experiment batches 100 records per serializer call. Its purpose is to determine whether grouping work at that size reduces repeated serialization overhead while keeping resource use acceptable. The experiment should run against the same 10,000-record workload used for the baseline and compare p95 latency plus memory consumption. Using the same workload, percentile, and endpoint behavior makes the result directly comparable with the 1,240 ms baseline.

The outcome should be assessed as a tradeoff rather than from latency alone. A lower p95 would support the batching approach, but the accompanying memory result is necessary because batching may change the amount or lifetime of data held during serialization. Functional output should also remain unchanged so a performance gain does not come from omitting or altering response data. If the result is inconclusive, the measurements should be reviewed before expanding the scope; the current evidence specifically identifies serialization and does not justify unrelated database changes.

Next action

Run the 100-record batching experiment against the 10,000-record workload and record p95 latency and memory alongside the 1,240 ms baseline.