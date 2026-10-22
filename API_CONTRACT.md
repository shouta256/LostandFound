# Lost & Found Tracker - Workflow Notes

[openapi.yaml](openapi.yaml) is the sole API reference for the CM333 MVP; this file records confirmed business rules and R3 only.

## Confirmed Decisions

| ID | Rule |
| --- | --- |
| D1 | MVP includes US1-US11; US6 is medium priority and the others are high priority; US12-US15 remain future features. |
| D2 | Use Google login and a one-hour application bearer token stored in frontend memory, with no refresh token. |
| D3 | New users are students; team members are assigned manually by the backend; no Google domain restriction applies and self-review is forbidden. |
| D4 | Keep ItemCreate's six required fields and existing validation limits; category is free text. |
| D5 | Create items as available and claims as pending; allow multiple claimants but only one approval, without automatically rejecting other claims. |
| D6 | Found items follow available -> claimed -> returned; lost items follow available -> returned; only team members change status, with no reversal or cancellation. |
| D7 | Ban own-listing claims and a second pending claim by the same user for the same item; allow reapplication after rejection while the item is available, with no withdrawal. |
| D8 | Search fields, newest-first ordering, and pagination are defined by OpenAPI's q, limit, and offset parameters. |
| R1 | Rejection status codes and error codes are defined in each OpenAPI operation. |
| R2 | Approval, pickup readiness, and physical return are separate stages; pickup access and data are defined in OpenAPI. |

## Workflow

- Submission leaves the item available; approval and the change to claimed succeed together; rejection leaves the item unchanged.
- Other pending claims require explicit review and cannot be approved while the item is claimed or returned; a manual change to claimed also requires an approved claim.
- Browse/search excludes returned items, which remain accessible by ID; claimants retain access to their pending/rejected claims without pickup data.
- Approval leaves pickup unset; team members then set its location and readiness, and actual handover uses the existing item-status operation to mark the item returned.
- The server records ready_at when pickup becomes ready, preserves it while ready, and clears it when not ready.
- Repeating the same decision/status preserves reviewer and timestamps; self-review remains forbidden, including repeated requests.
- Trim text before length validation, preserving internal whitespace and case; required text cannot be blank.

## Implementation-Time Question

**R3:** Confirm deployment host/allowed origins and Google client configuration, plus server-side logout/revocation if required.

Basis: Milestone 3's US1-US11 acceptance criteria, Milestone 5's claim/pickup model, and the confirmed D1-D8 and R1-R2 decisions; no API implementation is included.
