Added

This release adds WebAuthn login, giving users a modern authentication option based on public-key credentials. For the product, this expands the available login experience beyond existing methods and creates a foundation for stronger, phishing-resistant authentication. Engineering, support, and documentation teams should treat WebAuthn as a newly available path that may require updated onboarding guidance, troubleshooting material, and test coverage across supported browsers and authenticators. The release also adds audit events. These events improve the system’s ability to expose security- and operations-relevant activity for investigation, governance, and customer support. The change fixture does not specify event names, retention behavior, or configuration requirements, so those details should not be assumed in rollout communications.

Changed

The default list page size changes from 20 to 50. Consumers that rely on the server default will therefore receive more records per page without changing their requests. This can reduce the number of requests needed to traverse a list, but it also changes response volume and may affect rendering, processing time, memory use, or tests that assume the prior default. Integrations that already provide an explicit page-size parameter should be reviewed against their own configured behavior rather than assumed to inherit the new default. Product documentation, examples, and automated assertions that describe or expect a default of 20 should be updated to reflect 50.

Breaking

The old token endpoint is breaking: the legacy `/token` endpoint has been removed, and clients must use `/oauth/token`. Any integration that still calls the legacy path will no longer complete its token request successfully after adopting this release. This is the highest-priority compatibility concern because it can prevent authentication rather than merely alter response sizing or add optional functionality. Owners should identify callers by checking client configuration, deployment settings, code references, and relevant operational telemetry. Migration guidance should state the replacement path exactly and avoid implying that the legacy endpoint remains available as a fallback. Authentication flows should be exercised end to end after the endpoint is updated, including token acquisition and the subsequent use of issued tokens.

Next action

Before rollout, assign an owner to inventory every production client still calling `/token`, migrate each one to `/oauth/token`, and verify successful token acquisition in its deployment environment.
