Before

Migration M-17 changes the account identifier field from `account.handle` to `account.slug`. Before the migration, application code and operational workflows read the existing `handle` column. The principal compatibility concern is avoiding an abrupt cutover that could break callers still expecting that field. The migration therefore treats the rename as a staged transition rather than an immediate removal. The old column remains readable for one release, giving dependent code a defined compatibility window in which to move reads to `slug`. This window should be treated as temporary: it supports orderly adoption, but it does not change the intended destination or justify new dependencies on `handle`.

After

After the cutover, `account.slug` is the field that application code should use. Existing rows must be populated as part of the migration so that reads through the new field remain complete. The backfill is resumable: it records a cursor and can resume after interruption. That design limits the operational impact of a worker restart or paused deployment because completed progress does not need to be discarded and the process can continue from its recorded position. During the compatibility release, teams can validate new-field reads while the old field is still available. Completion should be assessed through the migration's actual state and cursor, without assuming an unreported row count, duration, or throughput target.

Rollback

Rollback is supported only while the old schema remains intact. Operationally, rollback stops before drop: the decision to reverse must be made before the drop-column step begins. Up to that boundary, the retained `handle` column provides the schema needed to return application reads to the prior path. Once the old column has been dropped, the documented recovery path is restoration from backup rather than an ordinary rollback. The deployment runbook should make this boundary explicit, and the drop should be treated as a separately controlled action after the compatibility release and backfill verification. If validation exposes a problem beforehand, pause the migration, preserve the cursor, and either resume the backfill after correction or roll application behavior back while the old column is available.

Next action

The release owner should add a deployment gate that verifies the resumable backfill has completed and all production reads use `account.slug` before authorizing the drop-column step.
