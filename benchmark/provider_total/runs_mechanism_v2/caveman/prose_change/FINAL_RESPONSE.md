Added

This release adds WebAuthn login, giving users and client applications a modern authentication option based on public-key credentials. For engineering and product teams, this expands the supported login surface and creates an opportunity to reduce dependence on passwords where WebAuthn enrollment and authentication are available. Rollout planning should account for user education, credential registration, browser and device behavior, recovery paths, and support readiness, even though those operational details are not specified in the change record.

The release also adds audit events. These events should improve visibility into relevant system activity and give operations, security, and support teams more information for investigation and accountability. The change record does not define event schemas, retention, delivery, or coverage, so consumers should validate those details before building monitoring or compliance workflows around the new events.

Changed

Default list page size changes from 20 to 50. Consumers that omit an explicit page-size parameter will therefore receive up to 50 records per page instead of 20. This may reduce the number of pagination requests needed for larger result sets, but it can also increase response payloads, processing time, memory use, and work performed per request. Integrations that rely on stable batch sizes, page counts, latency assumptions, or rate-limit calculations should set page size explicitly and test pagination behavior against the new default. No other pagination semantics are described in the change record.

Breaking

The old token endpoint is breaking: legacy `/token` has been removed, and clients must use `/oauth/token`. Any integration that still calls `/token` will fail after adopting this release, making endpoint migration a release-blocking compatibility requirement rather than an optional cleanup. Owners should search application code, deployment configuration, secrets-backed settings, SDK wrappers, automation, tests, examples, and operational runbooks for the legacy path. They should also confirm that requests to `/oauth/token` use the expected authentication method and payload, then exercise both successful and rejected token flows in a representative environment. The change record does not promise a compatibility redirect or grace period, so planning should assume the removed path is unavailable.

Next action

Before rollout, assign an owner to inventory every token client, replace each `/token` call with `/oauth/token`, and record passing integration-test evidence for every migrated client.
