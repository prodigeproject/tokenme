Added

This release adds WebAuthn login, giving users a modern authentication option based on registered authenticators rather than relying solely on traditional credentials. For engineering management, the important delivery consideration is that the feature will need the same operational attention as any other login path: teams should ensure that rollout, support guidance, and authentication monitoring account for WebAuthn flows. The release also adds audit events. These events provide an additional source of operational and security context that downstream consumers can incorporate into their existing review processes. Together, the login capability and audit visibility expand both the user-facing authentication surface and the information available to teams responsible for oversight.

Changed

The default page size for list responses changes from 20 to 50. Consumers that rely on the default, rather than specifying a page size explicitly, will receive more records per page after adopting this release. That can reduce the number of requests needed to traverse a result set, but it also changes response volume and may affect assumptions in user interfaces, batch processing, request timing, memory use, and tests. Integrations that already set an explicit page size should review their behavior, while integrations that accept the default should be checked for any logic tied to the previous value. Documentation and examples should consistently describe 50 as the new default so that implementation expectations remain aligned.

Breaking

The old token endpoint is breaking: the legacy `/token` endpoint has been removed. Any integration that still calls that path will no longer be able to obtain tokens through it and must migrate to `/oauth/token`. This is the highest-priority compatibility issue in the release because it can interrupt authentication for clients that have not updated their endpoint configuration. The migration should cover application code, environment variables, deployment configuration, secrets-management references, API clients, automated tests, runbooks, and examples wherever the legacy path may have been copied. Teams should treat successful token acquisition through `/oauth/token` as a release-readiness requirement and should not assume that an integration is safe merely because its other API calls continue to work.

Next action

Assign an owner to inventory every client and deployment for `/token`, replace each occurrence with `/oauth/token`, and verify successful token acquisition in the target environment before rollout.