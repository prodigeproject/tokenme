Baseline

The report endpoint currently measures 1,240 ms at p95 when processing 10,000 records. This is the reference point for evaluating any optimization work. It is important to retain the same workload and percentile measurement during the experiment so the comparison reflects a genuine change in endpoint behavior rather than a change in test conditions. The baseline should therefore be treated as the control result, with memory observed alongside latency to ensure that an apparent speed improvement does not simply shift pressure to another resource.

Bottleneck

CPU profiling identifies JSON serialization as the bottleneck, accounting for 61% of execution time. The database query is explicitly not the primary source of the delay. This evidence narrows the optimization target and argues against spending the current iteration tuning query execution or changing data access behavior. The relevant cost is incurred while converting the report data into its response representation, so the investigation should remain focused on how serialization work is organized and on whether that work creates avoidable CPU or memory pressure.

Experiment

The proposed experiment batches 100 records per serializer call. The intent is to test whether processing bounded groups reduces the serialization overhead seen in the profile while preserving the endpoint's output and operational behavior. The experiment should compare p95 against the 1,240 ms baseline and record memory behavior during the same run. Both measures matter: a lower latency result would be less compelling if batching materially worsened memory use, and stable memory without a latency improvement would not address the identified bottleneck.

The comparison should use the same 10,000-record workload as the baseline and keep surrounding conditions consistent. Output correctness should also be checked so batching does not alter record content, ordering, or the JSON response contract. After the run, another CPU profile can confirm whether serialization consumes a smaller share of execution time or whether the work has merely moved elsewhere. This makes the result useful even if the latency change is limited, because it will show whether the batching hypothesis directly affects the measured hotspot.

Next action

Implement an isolated batching prototype that sends 100 records through each serializer call, then run it against the same 10,000-record workload and compare p95, memory, output correctness, and the CPU profile with the baseline. Use those results to decide whether batching should proceed toward production or whether serialization needs a different optimization approach. The concrete next action is to run this controlled batching experiment and document the comparison.
