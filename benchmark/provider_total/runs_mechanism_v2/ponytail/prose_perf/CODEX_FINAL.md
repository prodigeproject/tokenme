Baseline

The report endpoint currently has a baseline latency of 1,240 ms at p95 when processing 10,000 records. This establishes the performance reference point for evaluating any change. The baseline is specific enough to support a controlled comparison: the same endpoint, workload size, percentile, and surrounding conditions should be retained when the experiment is run. The goal of the next measurement is not merely to show that one run is faster, but to determine whether the proposed change produces a repeatable improvement at the latency percentile that matters for slower user requests.

Bottleneck

CPU profiling identifies JSON serialization as the bottleneck. It accounts for 61% of the measured processing time, while the database query is not the primary source of delay. This distinction matters for prioritization: database tuning would address the wrong part of the request path and is therefore unlikely to produce the most meaningful improvement. Engineering effort should remain focused on how records are passed through the serializer and on the runtime and memory behavior of that work. The profile gives a credible reason to test a serialization-focused change, but it does not by itself prove how much end-to-end latency the change will remove.

Experiment

The experiment batches 100 records per serializer call. Its result should be compared with the existing behavior using p95 latency and memory consumption, as specified in the performance notes. Keeping the 10,000-record workload and the rest of the test setup unchanged will isolate batching as the relevant variable. Both measures are necessary: a latency improvement would be less useful if it introduced unacceptable memory pressure, while stable memory without a meaningful p95 improvement would not justify adopting the change. The evaluation should use repeated, comparable runs so that normal runtime variation is not mistaken for a reliable gain. No target improvement should be assumed before measurement because the available evidence supplies a bottleneck profile and experimental design, not a forecast.

Next action

Run the 100-record batching experiment against the same 10,000-record workload, record p95 latency and memory consumption alongside the 1,240 ms baseline, and use those results to decide whether to adopt the batching change.