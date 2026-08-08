Threat

The upload flow accepts an untrusted filename, creating a path traversal threat. An attacker can supply parent-directory segments such as `../` or provide an absolute path so that the resolved destination points outside the intended upload root. If the application uses that filename directly, or validates only its textual form, the attacker may cause a write to an unintended location. The security boundary is therefore not the apparent prefix of the submitted string; it is the actual filesystem location reached after path resolution. This matters because superficially different names can resolve to the same target, and a filename that appears to sit beneath the upload directory can escape it once traversal segments or absolute-path semantics are applied.

Control

The appropriate control is canonicalization plus containment. Build the candidate destination relative to the configured upload root, canonicalize it so traversal and other path-resolution effects are accounted for, and then require the canonical candidate to remain under the canonical upload root. Reject the upload whenever that containment check fails, including when the submitted value is an absolute path or uses `../` to escape. The comparison should use filesystem-aware path operations rather than string-prefix matching, since a textual prefix can confuse sibling paths with descendants. This design directly addresses the stated path traversal threat by making the authorization decision against the resolved path and a clearly defined root. Validation failure should stop the file operation rather than attempting to repair or reinterpret an unsafe filename.

Residual risk

Canonicalization and containment do not fully secure the later file open. The residual risk is symlink replacement: after validation but before open, an attacker may replace a directory in the validated path with a symlink. The subsequent open can then follow that symlink to a location outside the upload root even though the earlier canonical candidate passed containment. This is a time-of-check/time-of-use race, so repeating the same pathname validation does not make the validation and open atomic. The exposure depends on whether an attacker can modify relevant directories or links during that interval, but the fixture establishes that the race remains and should be treated as unresolved rather than covered by canonicalization alone.

Next action

Have the upload-path owner implement the canonicalization-and-containment rejection and change the final file creation to use a no-follow open primitive where available, then add a focused test that replaces an intermediate directory with a symlink between validation and open and verifies that the upload is rejected.