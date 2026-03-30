---
name: google-tasks
description: Manage Google Tasks -- list, create, complete, update, and search tasks. Use when the user mentions tasks, todos, reminders, or asks to check/add/complete tasks.
---

# Google Tasks

Manage the user's Google Tasks via the google-tasks MCP server.

## Available Tools

| Tool | Purpose |
|------|---------|
| `listProviders` | List available providers |
| `listTaskLists` | Get all task lists |
| `getTasks` | Fetch tasks from a specific list |
| `createTask` | Add a new task |
| `updateTask` | Modify an existing task |
| `completeTask` | Mark a task as complete |
| `deleteTask` | Remove a task |
| `searchTasks` | Search across all lists |
| `syncAllTasks` | Retrieve all tasks globally |

## Workflow

1. **Always start with `listTaskLists`** to get list IDs
2. Then use `getTasks` with the list ID to fetch tasks
3. Present tasks in a clean table: title, due date, status, notes

## When Creating Tasks

- Ask for a title at minimum
- Set due date if mentioned or implied
- Add notes for any extra context
- Assign to the default list unless user specifies otherwise

## When Listing Tasks

- Show overdue tasks first, highlighted
- Group by list if multiple lists exist
- Include notes/descriptions when present
- Omit completed tasks unless explicitly asked

## Proactive Use

If during a conversation you discover something that should be tracked as a task (e.g., "I need to book that appointment", "remind me to check X"), offer to create a Google Task for it.
