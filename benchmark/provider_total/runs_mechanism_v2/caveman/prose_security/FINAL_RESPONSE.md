Threat

The upload flow accepts an untrusted filename, making path traversal the primary threat. An attacker can supply a name containing `../` segments to move resolution outside the intended directory, or provide an absolute path that points somewhere else from the outset. If the application treats that input as a safe relative filename, the resulting file operation may target a location beyond the upload root. The security boundary therefore cannot depend on string shape, a prefix check against raw input, or an assumption that callers provide ordinary filenames. The relevant question is where the operating system will resolve the complete candidate path when the upload is opened.

Control

The required control is canonicalization plus containment. First, construct the candidate path and canonicalize it so that traversal components and other path-resolution effects are represented by the effective path. Then require that canonical candidate to remain under the canonical upload root before allowing the open. Both parts matter: canonicalization gives validation a resolved path to assess, while containment enforces the intended directory boundary. A candidate that resolves to the root itself or a permitted descendant can proceed according to the upload policy; one that resolves elsewhere must be rejected. This directly addresses both `../` traversal and absolute-path input because acceptance depends on resolved location, not the filename's apparent syntax.

Residual risk

Symlink replacement remains a residual risk even after correct validation. A race exists between validation and open: after the application confirms containment, an attacker may replace a directory in the validated path with a symlink. The subsequent open can then follow a different path from the one that passed validation and escape the upload root. Canonicalization and containment do not, by themselves, make those two operations atomic or prevent filesystem state from changing between them. Risk depends on whether an attacker can modify relevant directories during that interval, but the race must still be treated as part of the design rather than assumed away. Where the platform provides one, a no-follow open primitive should be used so opening the file does not follow a substituted symlink.

Next action

Update the upload open path to use the platform's available no-follow open primitive, while retaining canonicalization and the requirement that the candidate remain under the upload root.
