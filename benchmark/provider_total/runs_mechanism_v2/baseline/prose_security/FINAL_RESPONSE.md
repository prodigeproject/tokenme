Threat

The upload path accepts a filename supplied by an untrusted party. The primary threat is path traversal: an attacker can submit a name containing `../` segments or provide an absolute path in an attempt to escape the intended upload location. If the application joins that value to the upload directory and opens the result without validating the resolved destination, the write could target files elsewhere on the filesystem. The security boundary is therefore not the spelling of the submitted filename; it is the actual location reached after the operating system resolves the path. This matters operationally because checks that only reject obvious text patterns can miss alternate representations and normalization effects. A successful traversal could let an upload overwrite or create a file outside the area the service is meant to control.

Control

The required control is canonicalization plus containment. The service should construct the candidate path, canonicalize it, and then require the canonical result to remain under the canonical upload root before opening the destination. Canonicalization gives the comparison normalized paths after traversal components and path forms have been resolved. The containment test enforces the real policy: every accepted destination must be a descendant of the upload root, rather than merely sharing a textual prefix or originating from a concatenation with that root. Both parts are necessary. Canonicalization without a containment decision only describes the destination, while a containment check on a noncanonical string can approve a path that later resolves elsewhere. Invalid candidates, including escaping relative paths and absolute paths outside the root, should be rejected before any file operation occurs.

Residual risk

The residual risk is symlink replacement. Even after the candidate passes canonicalization and containment validation, an attacker may replace a directory in the validated path with a symlink between validation and open. The subsequent open can then follow a different filesystem route from the one that was checked. This is a time-of-check-to-time-of-use race, so repeating a conventional path check does not by itself make the final open atomic with validation. Exposure depends on whether an attacker can modify relevant directories, but the design should not assume that the earlier pathname decision remains true at use time. The fixture specifically calls for a no-follow open primitive where one is available, because the decisive protection must apply while the file is being opened.

Next action

Implement the upload open operation with an available no-follow primitive, while retaining canonicalization and upload-root containment, and add focused tests covering `../`, absolute paths, and directory-to-symlink replacement.
