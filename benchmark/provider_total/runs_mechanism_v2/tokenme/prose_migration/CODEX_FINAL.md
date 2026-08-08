Before

Migration M-17 begins with account data stored under `account.handle`. The migration’s purpose is to rename that field to `account.slug` while controlling compatibility and recovery risk. The important starting constraint is that existing readers may still depend on the old column. For that reason, the transition cannot treat the rename as an immediate removal of `account.handle`. The old column remains readable for one release, giving dependent code a defined compatibility window in which to move reads to `account.slug`. This release boundary should be treated as part of the migration contract: consumers need to complete their transition before the later drop-column step removes the old representation.

After

When M-17 is in progress, `account.slug` is the destination column and `account.handle` remains available for reads during the stated compatibility release. Existing account values are transferred through a backfill. The backfill records a cursor, so the backfill is resumable after an interruption instead of requiring an all-at-once run. Operationally, the cursor provides the continuation point for restarting the work and allows progress already represented by that cursor to be retained. Completion should therefore be assessed from the migration’s recorded state, not inferred merely from whether one execution ended without an interruption.

The intended end state is that consumers use `account.slug` and no longer require reads from `account.handle`. Dropping the old column is a separate, consequential boundary rather than an incidental part of the rename. Before crossing it, the team should confirm that the compatibility window has served its purpose, that the backfill has completed, and that remaining consumers have stopped relying on the old name. These are readiness conditions, not additional claims about automated enforcement in M-17.

Rollback

Rollback is supported until the drop-column step. Accordingly, rollback stops before drop: if reversal may be needed, it must be initiated before `account.handle` is removed. Once the drop-column step has run, the documented recovery path changes from rollback to restore from backup. This makes the drop the migration’s irreversible operational checkpoint. The release owner should avoid authorizing that checkpoint while backfill completion, consumer migration, or release readiness remains uncertain. The resumable backfill reduces interruption risk, but it does not extend rollback support beyond the column drop or replace the need for a valid backup after that point.

Next action

Have the release owner document and verify a pre-drop checklist covering completed backfill state, migration of all reads to `account.slug`, expiration of the one-release compatibility window, and backup readiness before authorizing the drop-column step.