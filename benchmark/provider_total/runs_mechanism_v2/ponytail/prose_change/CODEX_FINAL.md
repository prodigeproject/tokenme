Added
=====

This release adds WebAuthn login, giving users a new authentication option based on public-key credentials. For the product and engineering teams, this is the primary user-facing capability in the release. It should be reflected in release communications, authentication documentation, and support guidance so customers understand that WebAuthn is now available and know how it fits alongside their existing login methods.

The release also adds audit events. These events improve the information available for operational review and customer audit workflows. Teams that consume or document audit data should confirm that their materials describe the newly available events and that downstream handling remains appropriate. No further event names, schemas, volumes, or retention behavior are specified in the supplied change record, so those details should not be assumed as part of this report.

Changed
=======

The default list page size changes from 20 to 50. Requests that rely on the default will therefore return up to 50 items per page instead of 20. This may alter response sizes, the number of pagination requests, user-interface behavior, and assumptions in tests or integrations that did not set an explicit page size. Consumers that require stable pagination behavior should specify their intended page size rather than inheriting the new default. Documentation and examples that describe or implicitly demonstrate the former default should be reviewed for consistency with 50.

Breaking
========

The old token endpoint is breaking: the legacy `/token` endpoint has been removed. Clients and integrations that still call that path will no longer be able to obtain tokens through it. The supported replacement is `/oauth/token`, and callers must migrate to that endpoint. This is a direct compatibility break, not merely a deprecation notice, because the legacy route is absent in this release. Authentication failures are therefore expected wherever deployed configuration, application code, scripts, examples, or tests continue to reference `/token`.

The release should be treated as requiring integration readiness checks even if a client does not plan to adopt WebAuthn immediately. WebAuthn and audit events are additive, while the endpoint removal requires action from affected consumers. The page-size change is not identified as breaking, but it can still produce observable differences for callers that depended on the previous implicit value.

Next action
===========

Before rollout, inventory every production client and integration for calls to `/token`, replace each occurrence with `/oauth/token`, and verify token acquisition in a staging environment.