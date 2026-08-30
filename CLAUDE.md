# CLAUDE.md

This file guides AI assistants (including Claude) working in this repository. It doesn't hold task instructions itself — it points to the skill or file that does, so instructions live in one place and don't drift out of sync here.

## Repository Overview

**Repository**: Montiwebster1/Montiwebster1

This repo holds cross-cutting guidance for Monti's work, not a codebase. There's no build, no tech stack, no app to run here — if that changes, document the actual structure and commands when they exist, rather than in the abstract.

## Task Routing

For each kind of task, use the skill below instead of improvising:

**DBR engineering (plumbing design)**
- RFIs, submittals, sketches, permit comments, coordination issues → `engineering-review`
- Formal submittal compliance review against spec/drawings → `submittal-review`
- Reading a plan set, letter, or contract for a plain-English brief → `pdf-summariser`
- Project specs / SOWs → `spec-builder`

**Wise AI Partners (automation/AI)**
- Building or editing a skill → `skill-creator`
- Building an MCP server → `mcp-builder`
- Recurring/scheduled tasks → `loop`
- Session review to improve skills/memory → `improve-system`

**Sagemont Congregation**
- Announcements, resolutions, elder body letters, notices → `congregation-communications-drafter`
- Talks and meeting parts → `talk-part-builder`
- Meeting notes → action items → `meeting-to-action-items`

**Cross-cutting / general**
- Spreadsheets (clean, build, fix) → `xlsx` / `clean-messy-spreadsheet`
- Receipts and expense tracking → `organise-receipts-and-expenses`
- Writing that should sound like Monti → `personal-voice` / `humanizer` / `voice-agent`
- Messy, unstructured requests → `prompt-master`
- Documents (Word/PDF/PPTX) → `docx` / `pdf` / `pptx`
- End-of-session audit → `starter-session-audit`

If a task doesn't map to any of these, don't force-fit it — ask, or handle it directly and flag that it may be worth a new skill (`skill-creator`).

## Git Workflow

- Use descriptive, focused commit messages.
- Push changes to feature branches, not directly to main.

## Goal Alignment & Safeguards

Before starting any new project or building any automation in or from this repository, confirm it clearly serves one of Monti's broader goals — DBR engineering business goals, Wise AI Partners (automation/AI) goals, Sagemont Congregation service goals, or another personal goal he's stated — and check that it doesn't conflict with or work against the others (e.g. an automation that saves time on one front but creates risk or extra burden on another). If the linkage isn't clear, ask before building.

## Updating This File

When a new recurring task type shows up, add a routing line above pointing to the skill (or new file) that should handle it — don't inline the instructions here.
