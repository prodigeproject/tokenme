Answer

The upload API response indicates rate limiting, not an authentication failure or credential compromise. HTTP 429 means rate limit. The client should stop issuing immediate repeat requests, wait for the interval specified by the server, and then retry. In this case, the response contains `Retry-After: 30`; Retry-After is authoritative and should determine when the next attempt occurs. Credentials need not be rotated. Rotation would not resolve throttling and would add operational work without addressing the reported condition.

Evidence

The customer reported HTTP 429 from the upload API. That status directly identifies the request as rate-limited. The same response includes `Retry-After: 30`, giving the client an explicit server-provided delay to honor before trying again. The request was authenticated, so the available evidence does not point to invalid credentials. In addition, no credential exposure appears in the logs. Together, these facts support treating the event as a capacity or request-rate control response rather than a security incident or authentication defect.

The prescribed client behavior is also consistent with the response: back off and retry after the authoritative interval. Repeating the upload sooner could encounter the same limit and prolong recovery. Changing credentials would not change the applicable rate-limit condition, so it is not a corrective measure for this response.

Limit

This assessment is limited to the information in the support record. It does not identify what quota or rate-limit policy was reached, whether the limit applies to a client, account, endpoint, or another scope, or whether multiple callers contributed to the condition. It also does not establish whether the upload succeeded on a later attempt. No conclusions should be drawn about those points without request telemetry, retry results, or the relevant service policy.

The absence of credential exposure in the reviewed logs supports the current conclusion, but it is not a general guarantee about every system or log source. If separate evidence of compromise emerges, that evidence should be handled through the normal security process; the HTTP 429 itself is not a reason to rotate credentials.

Next action

Update the upload client to honor `Retry-After: 30` by waiting for that server-specified interval before retrying the failed request.