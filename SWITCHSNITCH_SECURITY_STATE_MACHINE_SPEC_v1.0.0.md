# Lokivelli's ChatGPT SwitchSnitch — Frozen Security & State-Machine Specification

Version: 1.0.0
Status: FROZEN

## Normative invariants

1. The expected model is explicitly operator-defined. It is never learned by TOFU or changed by ACCEPT.
2. Browser-to-bridge requests are authenticated by a manually provisioned per-install token sent in a request header, never a query parameter. Token rotation is blocked while an actionable mismatch is pending unless the operator explicitly expires that event.
3. Model strings never cross the notification shell command boundary. Notification actions carry only an opaque mismatch ID and decision verb.
4. Each actionable mismatch binds mismatch_id, surface_id, chat_id, expected_at_event, selected_at_event, observed_at_event, monotonic sequence, creation/expiry timestamps, token fingerprint, and lifecycle state.
5. Only the owning surface may receive a decision. Non-owning callers receive SURFACE_MISMATCH. surface_id and chat_id are revalidated immediately before RESTORE_ATTEMPTED. CHAT_CHANGED is NO-OP.
6. A new actionable mismatch for the same surface supersedes the previous pending mismatch, receipts MISMATCH_SUPERSEDED, and replaces the Android notification for that surface.
7. Decisions have a TTL. Expired, superseded, already-issued, wrong-surface, wrong-chat, or expected-changed decisions cannot restore.
8. Decision issuance and execution are distinct: DECISION_ISSUED precedes RESTORE_ATTEMPTED; retries after issuance are NO-OP / ALREADY_ISSUED.
9. ACCEPT suppresses the same (surface_id, chat_id, observed_model) for a bounded interval. It does not change expected. SET_EXPECTED is a separate explicit operator action and receipt.
10. Detection is stability-gated. Unstable reads create no mismatch. Stable wrong reads may create actionable MISMATCH_DETECTED. Stable unreadable reads create passive OBSERVED_MODEL_UNVERIFIED only.
11. OBSERVED_MODEL_UNVERIFIED is never RESTORE-capable.
12. RESTORE verification uses a bounded re-observation window and records the final value, including third-value and timeout cases.
13. NOTIFICATION_FAILED is passive-only and cannot become an actionable restore. Bridge/notification degradation is exposed to the extension and overlay distinctly from model mismatch.
14. RESTORE_FAILED closes that attempt; continued stable mismatch creates a fresh event with predecessor_id referencing the failed event.
15. Receipts carry schema_version, spec_version, spec_sha256, install-local monotonic receipt_sequence, event type, timestamps, token fingerprint, and applicable mismatch/surface/chat state.
16. Receipt sequence survives restart. Startup tolerates a truncated tail, emits RECEIPT_RECOVERED, and terminal/security events are fsynced. Rotation never silently deletes evidence.
17. AUTH_REJECTED is receipted and rate-limited by aggregation, not silently dropped.
18. Runtime startup validates the frozen specification hash. A missing/mismatching artifact makes conformance fail and enters a distinct degraded/nonconformant state. Tests/protocol claims citing a different hash fail conformance and receipt that failure.
19. The bridge records the validated spec hash at startup and binds it to every receipt.
20. Termux notification action to bridge uses a Unix-domain socket. SO_PEERCRED is UNVERIFIED until tested on the target S24/Termux environment. If unavailable, the documented fallback is filesystem-permissions-only and is explicitly receipted as a weaker posture.
21. Until on-device evidence proves another action channel, successful Android notification delivery is required for actionability.
22. The Hotkey overlay must remain FLAG_NOT_FOCUSABLE and must not alter browser focus, IME state, cursor, selection, or browser scroll position through slide-in/out.

## Lifecycle

DETECTED -> NOTIFIED -> DECISION_PENDING -> DECISION_ISSUED -> RESTORE_ATTEMPTED -> RESTORE_VERIFIED | RESTORE_FAILED

Terminal/side paths include ACCEPTED, SUPPRESSED, SUPERSEDED, EXPIRED, AUTH_REJECTED, EXPECTED_CHANGED, SURFACE_MISMATCH, CHAT_CHANGED, NOTIFICATION_FAILED, ALREADY_ISSUED, OBSERVED_MODEL_UNVERIFIED, and explicit NO-OP.

## Frozen acceptance gates

GATE-1 LIVE_CHATGPT: live ChatGPT detection and restore on the target S24.
GATE-2 ANDROID_ACTIONABILITY: notification/bridge actionability under Android lifecycle including background/Doze behavior.
GATE-3 OVERLAY_IME: Hotkey Prompter overlay focus/IME invariance on the target S24: keyboard open/closed, mid-typing cursor/selection, portrait/landscape, gesture navigation, 3-button navigation, external keyboard/no IME, browser scroll position, slide-in and slide-out.
GATE-4 UNIX_PEER_SECURITY: actual SO_PEERCRED behavior on target S24/Termux. Failure does not silently upgrade the security claim; filesystem-permissions-only is an explicitly weaker fallback.

No gate is PASS until its target-device evidence exists. Overall status remains HOLD until GATE-1, GATE-2 and GATE-3 pass; GATE-4 determines the security claim the notification channel is entitled to make.
