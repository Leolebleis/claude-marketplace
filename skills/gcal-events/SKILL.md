---
name: gcal-events
description: Use when creating, updating, or managing Google Calendar events. Triggers on "add to my calendar", "create an event", "schedule", "book", "remind me on [date]", or when an appointment/meeting needs to be tracked. Ensures events have proper information hierarchy, HTML formatting, hyperlinks, and pre-event buffers.
---

# Google Calendar Events

Create well-structured, actionable calendar events with proper information hierarchy and formatting.

## Principles

1. **Most important information first** -- what you MUST do/bring goes at the top
2. **HTML formatting** -- bold, lists, hyperlinks (never bare URLs)
3. **Hyperlinks over raw URLs** -- `<a href="...">descriptive text</a>`, not `https://...`
4. **Sparse emoji** -- only for critical warnings (one or two max)
5. **Pre-event buffer** -- create a separate 15min "arrive early" event before in-person appointments
6. **Red for important** -- use colorId `11` (Tomato) for important events
7. **Useful reminders** -- day before + 2 hours + 30 minutes for important appointments

## Event Description Structure

```
[Critical action items -- what to bring/do, with warning emoji]

[What this event is -- one line]

[Reference numbers / IDs if relevant]

[Logistics -- arrival time, dress code, parking, etc.]

[Links -- emails, documents, portals]
```

## HTML Formatting Reference

The description field accepts HTML. Always use it:

```html
<b>Bold text</b>
<ul><li>List item</li></ul>
<a href="https://example.com">Link text</a>
<br> for line breaks
```

## Example

```
description: '<b>WARNING MUST BRING:</b>
<ul>
<li>Passport</li>
<li>Appointment confirmation (<a href="https://mail.google.com/...">confirmation email</a>)</li>
</ul>
<br>
Biometrics appointment (fingerprints + facial photograph).<br>
<br>
Ref: ABC-1234-5678<br>
<br>
Arrive 15 mins early. Clean fingertips.'
```

## Pre-Event Buffer

For in-person appointments with an "arrive early" requirement, create TWO events:

1. **Buffer event** (e.g. 15:00-15:15) -- title: "Arrive early to [appointment name]"
2. **Main event** (e.g. 15:15-16:15) -- the actual appointment with full details

## Color Coding

| colorId | Color | Use for |
|---------|-------|---------|
| `11` | Tomato (red) | Important appointments, deadlines |
| `7` | Peacock (blue) | Standard events |
| `5` | Banana (yellow) | Reminders, low priority |

## Reminders for Important Events

```json
[
  {"method": "popup", "minutes": 1440},
  {"method": "popup", "minutes": 120},
  {"method": "popup", "minutes": 30}
]
```

## What NOT to Do

- Never put bare URLs in descriptions -- always wrap in `<a>` tags
- Don't include information you'll have physically (e.g. passport number when you're bringing the passport)
- Don't bury critical actions below background context
- Don't skip the pre-arrival buffer for in-person appointments
- Don't use plain text formatting when HTML is available

## Tools (Google Calendar MCP)

| Tool | Purpose |
|------|---------|
| `create_event` | Create new event |
| `update_event` | Update existing event |
| `list_events` | List events in a time range |
| `get_event` | Get event details |
| `delete_event` | Delete an event |
