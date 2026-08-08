Finding

This review identifies a P1 performance issue in `billing/history.py`. The billing-history endpoint performs N+1 reads: it first loads the invoice collection and then runs one separate line-item query for every invoice row. That access pattern makes database work grow directly with the number of invoices returned, so the endpoint becomes increasingly expensive for tenants with larger billing histories. Because billing history is a user-facing workflow and the inefficient behavior is inherent in the current query shape, the issue should be treated as a high-priority production concern rather than a minor optimization opportunity.

Evidence

The reviewed endpoint loads invoices and then retrieves line items one invoice at a time. For a tenant with 400 invoices, this produces 401 reads: one read for the invoices plus 400 per-row line-item reads. This is the characteristic N+1 query pattern. It adds repeated database round trips and avoidable query overhead to a single request, with costs that rise as the result set grows.

The invoice query filters on `tenant_id` and `created_at`. The database engine supports a composite index on those columns, but the current implementation does not yet take advantage of that available indexing strategy. Together, the per-row line-item lookup and the unindexed multi-column filter leave both the query count and the initial invoice lookup in need of improvement. The observed 401-read case is sufficient to establish material amplification without relying on projections or invented traffic assumptions.

Recommendation

Replace the per-invoice line-item reads with a set-based loading strategy. Depending on the data-access layer, this can be implemented as an explicit join, eager loading, or a batched line-item query keyed by the invoice identifiers returned by the first query. The implementation should preserve tenant isolation and the endpoint’s existing response shape while ensuring that line-item retrieval uses a bounded number of reads instead of one read per row.

Also add a composite index covering `tenant_id` and `created_at`, ordered to match the endpoint’s filtering and history retrieval behavior. Verify the change with a focused regression test that creates multiple invoices with line items, asserts the returned billing history remains correct, and captures the query count so the N+1 pattern cannot silently return. Review the resulting query plan to confirm that the database uses the composite index for the invoice lookup.

Next action: assign the P1 fix to the billing owner to implement batched line-item loading and the composite index in the next production patch.
