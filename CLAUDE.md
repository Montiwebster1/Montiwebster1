# CLAUDE.md

This file provides guidance to AI assistants (including Claude) when working with this repository.

## Repository Overview

**Repository**: Montiwebster1/Montiwebster1
**Status**: Newly initialized repository

This repository is in its initial state. As the project develops, this file should be updated to reflect the codebase structure, conventions, and workflows.

## Project Structure

```
Montiwebster1/
├── CLAUDE.md                          # AI assistant guidance (this file)
├── scripts/
│   └── extract_subtitles.sh           # yt-dlp wrapper: pull subtitles for a YouTube URL
└── .git/                              # Git configuration
```

### Scripts

- **`scripts/extract_subtitles.sh <youtube-url> [output-dir] [sub-langs]`** — Wraps
  `yt-dlp` to download manual + auto-generated subtitles (VTT) for a video without
  downloading the video itself. Requires `yt-dlp` on PATH (`pip install -U yt-dlp`).
  Serves Wise AI Partners automation work (e.g. pulling transcripts for content/AI
  pipelines).

## Development Guidelines

### Getting Started

1. Clone the repository
2. Set up your development environment based on the chosen tech stack
3. Update this CLAUDE.md as project structure evolves

### Git Workflow

- Use descriptive commit messages
- Keep commits focused and atomic
- Push changes to feature branches, not directly to main

### Goal Alignment & Safeguards

Before starting any new project or building any automation in or from this repository, confirm it clearly serves one of Monti's broader goals — DBR engineering business goals, Wise AI Partners (automation/AI) goals, Sagemont Congregation service goals, or another personal goal he's stated — and check that it doesn't conflict with or work against the others (e.g. an automation that saves time on one front but creates risk or extra burden on another). If the linkage isn't clear, ask before building.

### Updating This File

As the project grows, update this CLAUDE.md with:

- **Build commands**: How to build, test, lint, and run the project
- **Architecture**: Key directories, modules, and their responsibilities
- **Dependencies**: Core libraries and frameworks used
- **Testing**: How to run tests, testing conventions, and coverage requirements
- **Code style**: Formatting rules, linting configuration, and naming conventions
- **Common patterns**: Architectural patterns and idioms used in the codebase
