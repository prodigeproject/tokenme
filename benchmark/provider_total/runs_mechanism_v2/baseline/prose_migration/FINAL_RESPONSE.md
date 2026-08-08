Before

Migration M-17 changes the account identifier column from `account.handle` to `account.slug`. Before the migration, application behavior and integrations read the existing `handle` field, so the principal delivery risk is not the schema rename itself but coordinating readers, writers, and existing data without creating an avoidable compatibility break. The migration plan therefore needs to preserve a safe transition window while data is copied and consumers move to the new name. The current fixture also establishes the recovery boundary: rollback is supported only while the old column still exists. Once the drop-column step has run, reversal is no longer a normal migration operation and recovery requires restoring from backup.

After

During the transition, the new `slug` column becomes the destination while the old column remains readable for one release. That compatibility period allows deployed code and dependent consumers to move away from `handle` without requiring every reader to change simultaneously. Existing records are migrated through a backfill that records a cursor. Because progress is checkpointed through that cursor, the backfill is resumable after an interruption instead of requiring completed work to be repeated from the beginning. Operationally, this makes interruption a recoverable event and gives the team a clear point from which processing can continue. After consumers have completed the transition and the compatibility release has passed, the old column can be considered for removal, subject to the rollback decision described below.

Rollback

The rollback procedure stops before drop: if validation or application behavior indicates that M-17 should be reversed, the team must halt before the drop-column step and roll back while `account.handle` is still present. At that point, the retained old column provides the supported route back to the previous application contract, and the migration can be paused without losing the original field. The resumable backfill can also remain interrupted safely because its cursor records progress. If the old column has already been dropped, the supported rollback window has ended; rollback cannot reconstruct the removed data through the migration itself, and restoration from backup is required. The drop is therefore the explicit point of no routine return and should be treated as a separately controlled action after compatibility and validation are complete.

Next action

Schedule an engineering readiness review for M-17 that confirms all consumers have moved to `account.slug`, verifies the saved backfill cursor can resume correctly, and explicitly approves or defers the drop-column step.
