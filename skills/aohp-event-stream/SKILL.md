---
name: aohp-event-stream
description: Register, drain, and stop AOHP Toast/notification event streams via the aohp CLI.
metadata: {"openclaw":{"emoji":"🔔","requires":{"bins":["aohp"]},"os":["linux"]}}
---

# AOHP event stream

Use this skill when transient Android UI feedback matters: Toasts, notification posts/removals, and heads-up notification visibility. The stream is opt-in and buffered by AOHP only after registration.

## Workflow

1. Register before the actions that may trigger transient feedback:

```bash
aohp event register --client openclaw --max 200
```

Save the returned `sessionId`.

2. After an action, drain recent events:

```bash
aohp event drain --session <sessionId> --format text
```

Use JSON when you need structured fields:

```bash
aohp event drain --session <sessionId> --format json -p
```

3. Ask for screenshots only when visual evidence matters. This may produce large output:

```bash
aohp event drain --session <sessionId> --screenshots --inline --format json
```

4. Always unregister when the task no longer needs events:

```bash
aohp event unregister --session <sessionId>
```

## Event fields

Events include `type`, `timeRealtimeMs`, `packageName`, `displayId`, `displayRole`, `activity`, `text`, and optional `notification` / `screenshots`.

Common `type` values:

- `toast`
- `notification_posted`
- `notification_removed`
- `heads_up_shown`
- `heads_up_hidden`

## Notes

- Register before triggering a Toast; Toasts disappear quickly and cannot be recovered later.
- Custom app-rendered Toasts may not expose text. AOHP still reports package, display, activity, and screenshots when available.
- Notification display attribution is best effort because Android notifications do not inherently belong to a display.
- `aohp event status` shows active sessions and buffer state.
