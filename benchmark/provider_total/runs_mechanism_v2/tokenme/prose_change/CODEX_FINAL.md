Added

This release adds WebAuthn login, giving users a modern authentication option based on public-key credentials. The capability can support passwordless sign-in flows and stronger resistance to credential phishing when clients and deployment environments are configured appropriately. Engineering and product teams should treat this as a new login path that needs coverage across enrollment, authentication, recovery, browser compatibility, and user-support documentation. Rollout planning should also define fallback and account-recovery expectations before the option is broadly enabled for users. The release also adds audit events. These events should be incorporated into the existing observability and security-review workflow so operators can confirm that relevant activity is recorded, retained, and available to the teams responsible for investigation and compliance.

Changed

The default list page size changes from 20 to 50. Consumers that rely on the default rather than specifying a page size will receive more records in each response. This may reduce the number of requests needed to traverse a list, but it can also change response payload size, rendering behavior, memory use, and assumptions in pagination tests. Services and user interfaces should continue to use explicit pagination parameters wherever predictable behavior matters. Test suites should verify navigation, terminal-page handling, and any latency or payload effects under representative data volumes.

Breaking

The old token endpoint is breaking: the legacy `/token` endpoint has been removed, and clients must use `/oauth/token`. Any integration that still calls the legacy path will no longer be able to obtain tokens after adopting this release. This is a direct compatibility break rather than a deprecation warning, so affected authentication flows can fail immediately. Owners should search application code, deployment configuration, secrets-management templates, API client wrappers, automation, examples, and operational runbooks for the old path. Updating only the primary application may be insufficient if scheduled jobs, command-line tools, partner integrations, or older deployed clients construct the token URL independently. Migration validation should confirm the new endpoint in a representative environment and exercise both successful token issuance and expected authentication failures.

Next action

Create and assign a migration ticket to inventory every `/token` caller, update each one to `/oauth/token`, and verify token issuance in a representative environment before this release is deployed.