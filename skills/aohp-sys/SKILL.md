---
name: aohp-sys
description: Clipboard, notifications, outbound SMS, device status, and wake or unlock helpers via the aohp CLI.
metadata: {"openclaw":{"emoji":"⚙️","requires":{"bins":["aohp"]},"os":["linux"]}}
---

# AOHP system helpers

Read or change lightweight **system state** through **`aohp sys <subcommand>`**, or send **outbound SMS** with **`aohp sms send`**. Prefer these commands for normal tasks.

## When to use

- Clipboard read/write, notification shade, quick device/battery/network/screen snippets, or wake / sleep / unlock helpers.
- Send an SMS to a saved contact (by display name) or a phone number.

## Commands

| Goal | CLI |
|------|-----|
| Clipboard get/set | **`aohp sys clipboard [-o get\|set] [-s <text>]`** — **`set`** requires **`-s` / `--text`** |
| Expand or collapse notifications | **`aohp sys notifications [-o expand\|collapse]`** (default **expand**) |
| Send SMS by contact name | **`aohp sms send -t Taylor -m "Hello"`** |
| Send SMS by phone number | **`aohp sms send -t 15551234567 -m "Hello"`** |
| Device info one-liner | **`aohp sys device-info`** |
| Battery summary | **`aohp sys battery`** |
| Network snippet | **`aohp sys network`** |
| Display snippet | **`aohp sys screen-info`** |
| Wake / sleep / unlock screen | **`aohp sys wake`**, **`sleep`**, **`unlock`** |

## Examples

```bash
aohp sys clipboard -o get
aohp sys clipboard -o set -s "pasted text"
aohp sys notifications -o collapse
aohp sys battery
aohp sys wake

aohp sms send -t Taylor -m "Hello!"
```

## Optional: raw JSON form

```bash
aohp call sys.clipboard '{"op":"get"}'
aohp call sys.clipboard '{"op":"set","text":"hello"}'
aohp call sys.notifications '{"op":"expand"}'
aohp call sms.send '{"contactName":"Taylor","body":"Hello"}'
aohp call sms.send '{"address":"15551234567","body":"Hello"}'
```

## Notes

- Clipboard may require an accessibility-based implementation on the agent; failures sometimes report missing accessibility service.
- **`device-info`**, **`network`**, **`screen-info`** return **plain text** snippets from the device; exact wording can vary by build.
- **`aohp sms send`**: **`contactName`** / **`-t`** with a name resolves against Contacts (exact match first, then partial). Phone numbers need at least 7 digits.
- For notification-driven SMS: register the event stream **before** the notification fires, drain after it arrives, then **`aohp sms send`**.
