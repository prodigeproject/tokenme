Finding

This review identifies a P1 performance finding in `billing/history.py`. The billing history endpoint performs N+1 reads: it first loads one invoice collection, then issues one additional line-item query for every invoice row returned. That access pattern makes database work grow with result size instead of fetching the required history in a bounded set of operations. Because this endpoint serves billing history, the issue affects a user-facing path where slow or overloaded reads can obstruct access to financially important records. Priority should reflect both the inefficient query shape and its ability to amplify database load as tenant history grows.

Evidence

The reviewed behavior is explicit: the endpoint loads invoices and then performs one line-item query per row. For a tenant with 400 invoices, the request creates 401 reads. One read retrieves the invoice data, while 400 more reads retrieve line items individually. This is direct evidence of the N+1 pattern, not a speculative concern based only on code style.

The query also filters by `tenant_id` and `created_at`. Those fields define the access path that must be efficient when billing history is selected for a tenant and ordered or constrained by time. The database engine already supports a composite index on those columns, so the repository does not face an engine capability blocker. Together, the repeated per-row reads and the multi-column filtering pattern create avoidable work on a request whose cost rises with invoice count. The 400-invoice example shows the operational shape clearly without requiring an extrapolated traffic estimate.

Recommendation

Refactor the endpoint so line items are fetched in bulk rather than once per invoice. Suitable production implementations include a join, a prefetch strategy, or one batched query keyed by the selected invoice identifiers; the final choice should preserve existing response semantics and avoid duplicate invoice data. Confirm through a focused query-count test that read count no longer increases once per returned invoice.

Add a composite index covering `tenant_id` and `created_at`, with column order chosen to match the actual filter and ordering behavior. Validate the resulting query plan to ensure the database selects that index, and run the billing history test suite to detect response or ordering regressions. Treat both changes as one performance correction: batching removes N+1 reads, while the composite index improves the remaining tenant-and-time lookup.

Next action: assign an owner to implement the bulk line-item fetch and composite index in the next change set.