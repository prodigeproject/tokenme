Finding

This review identifies a P1 performance issue in `billing/history.py`. The billing history endpoint performs N+1 reads: it first loads invoices and then issues one separate line-item query for each invoice row. That access pattern makes database work grow directly with the number of invoices returned, so the endpoint becomes progressively more expensive for larger tenants. Because billing history is a user-facing workflow and the cost is repeated on every affected request, the issue should be treated as an urgent production concern rather than a routine optimization.

The implementation also filters data by `tenant_id` and `created_at`. Without an index aligned to that filter shape, the database may do avoidable work while identifying the relevant tenant records and time range. The query pattern and indexing gap compound one another: the endpoint generates too many reads, and those reads may not use the most efficient lookup path. The appropriate remediation therefore has two parts—remove the per-row query behavior and add a composite index.

Evidence

The reviewed endpoint loads one invoice and then performs one line-item query per row. For a tenant with 400 invoices, the current behavior creates 401 reads. This is concrete evidence of the N+1 pattern: one initial read is followed by 400 additional reads, one for each invoice. No extrapolated latency, traffic, cost, or failure-rate figures are needed to establish the concern; the observed read count already shows that database round trips scale linearly with the result set.

The query filters on `tenant_id` and `created_at`, and the database engine supports a composite index on those columns. That makes the proposed index compatible with the existing query shape. The fixture does not provide execution plans or timing measurements, so expected latency improvement should be confirmed rather than estimated. Likewise, index column order and sort direction should be selected against the actual query, including its equality, range, and ordering behavior, then verified with the database query planner.

Recommendation

Refactor the endpoint to fetch line items in bulk for all returned invoices, or use an appropriate join or prefetch mechanism, and assemble the invoice-to-line-item relationship in application code if needed. This should reduce the request from a read count that grows per invoice to a bounded set of reads while preserving tenant isolation and response semantics.

Add a composite index covering `tenant_id` and `created_at`, using the column order that matches the production predicate and ordering. Validate the change with a representative 400-invoice tenant, compare query counts and execution plans before and after, and add a regression test that fails if per-invoice reads return. Review write and storage overhead during rollout, since every additional index has a maintenance cost.

Next action: assign an owner today to prepare the bulk-fetch change and composite-index migration for expedited review.