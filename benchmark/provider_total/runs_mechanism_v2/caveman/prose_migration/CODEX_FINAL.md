Before

Migration M-17 changes account naming from `account.handle` to `account.slug`. Before migration, application behavior and stored data rely on `account.handle` as existing readable field. Main delivery concern is compatibility while code and data move to new name. A direct rename or immediate removal would give dependent readers no transition period and would make recovery harder. Migration therefore treats introduction, data movement, adoption, and eventual removal as separate phases. This framing matters for engineering management because safe completion is not only schema change: it also requires confidence that reads have moved, backfill has completed, and rollback window remains open. Existing behavior must stay available during transition, with old column retained long enough for one release of compatibility.

After

Target state uses `account.slug` in place of `account.handle`. During transition, old column remains readable for one release, allowing application changes and dependent readers to move without an abrupt compatibility break. Data migration uses a recorded cursor, so backfill is resumable after interruption. Restarting work should continue from recorded progress instead of requiring migration to begin again. This reduces operational risk from deploy interruptions or bounded execution windows and makes progress easier to manage.

Completion should be judged in phases. First, new column and compatible application behavior become available. Next, backfill advances until all intended records have been processed. Readers then adopt `account.slug` while `account.handle` remains available for promised release. Only after compatibility period and migration checks are complete should drop-column step be considered. This sequence separates reversible work from destructive cleanup and gives team a clear point at which recovery options change.

Rollback

Rollback is supported only until drop-column step. Operational rollback stops before drop: if migration must be reversed, team must halt before old column is dropped and return application behavior to old readable field while it still exists. Cursor-based backfill does not need to be discarded merely because processing was interrupted; backfill can resume from saved cursor when migration proceeds again.

After drop-column step, normal rollback is no longer supported. Recovery then requires restoration from backup. This boundary should be treated as explicit approval gate, not routine continuation of backfill. Team should verify release compatibility period has elapsed, readers no longer depend on `account.handle`, backfill is complete, and backup recovery expectations are understood before authorizing drop.

Next action

Schedule review gate before drop-column step, with evidence that backfill completed from its recorded cursor and all readers use `account.slug` after one-release compatibility window.