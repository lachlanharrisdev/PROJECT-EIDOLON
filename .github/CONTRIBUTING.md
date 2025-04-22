# // CONTRIBUTING

![Banner](/.github/images/Banner_contributing_2x1.jpg)

First off, thank you for considering contributing to Project Eidolon. Whether you're a developer, documentor, or you have a lot of cash to burn on open-source projects, you're welcomed to the club.

This document outlines our process and rules for contributing. Read it before opening issues or pull requests, we want to keep everything organised, neat & streamlined.

## // WHAT IS PROJECT EIDOLON?

Project Eidolon is a modular, extensible system designed to detect, track, and analyze coordinated bot activity and narrative manipulation online. It’s part research tool, part surveillance system, part digital exorcist. If you're contributing, you're building tools to expose the unseen — treat that responsibility with care and cleverness.

## // GETTING STARTED

1. **Fork the repo** and clone your fork locally.
2. Install dependencies: `pip install -r requirements.txt` (or use the environment setup guide in `/docs`)
3. Work in a **feature branch**, never `main` directly.
4. Follow the code style and structure conventions (detailed below).
5. Open a pull request (PR) with a clear explanation of your changes.
6. Be ready for constructive feedback and/or dramatic praise.

## // CODE STYLE

- We use **PEP8** as baseline, or more specifically, the [Black code style](https://black.readthedocs.io/en/stable/index.html)
- Use **type hints** generously.
- Docstrings should follow **Google-style** or **reStructuredText**. If you explain a function like a tutorial for aliens, you're doing great.
- Commit messages should be clear and purposeful:
  - `fix: resolve tokenization bug in sentiment module`
  - `feat: add module support for Telegram ingestion`
  - `refactor: simplify graph clustering logic`

## // ARCHITECTURE

Eidolon is modular for a reason. When adding new functionality:

- If it ingests data → it's in `/ingest`
- If it processes or analyzes → it's in `/core`
- If it's a tool, visualization, or CLI interface → it's in `/interface`
- If it changes the system structure → open an issue first for discussion.
- Ensure you've updated the associated `__init__.py` file

Avoid hardcoded paths or platform-dependent logic. Eidolon is meant to run anywhere — from business-grade server rooms to raspberry pi's.

## // TESTING

- Tests live in `/tests`
- Add tests for new modules and logic-heavy components
- Use `pytest`, keep tests small and deterministic

## // DOCUMENTATION

If you add or change major functionality, document it in `/docs` and update any affected `README`s.

## // ISSUES && SUGGESTIONS

- Use GitHub Issues for bugs, features, or design proposals.
- Label clearly: `bug`, `enhancement`, `discussion`, `question`
- For large features or refactors, open a discussion or draft PR first.
- For more informal discussion, [join the discord](https://discord.gg/wDcxk4pCs5)

## // WHAT NOT TO DO

- Don’t push directly to `main`.
- Don’t open a PR without checking it runs and passes basic linting.
- Don’t write fragile or overly specific logic unless you absolutely have to.
- Don’t write code you’re not proud of — Eidolon deserves your A-game.

## // FIRST-TIMERS && EASY-FIXES

We label some issues as `good first issue` or `help wanted`. If you’re new, these are great places to start. If you’re confused, drop a comment or jump into discussions — we don't bite.

Additionally, you can [join the discord](https://discord.gg/wDcxk4pCs5) where you can ask questions more informally, & have friendlier discussion

---

## // FINAL WORDS

Project Eidolon isn’t just code — it’s an attempt to shine a light on coordinated misinformation in a way that's open, ethical, and technically beautiful. Contributions are not just welcomed — they’re celebrated. You’re not just another dev; you're a digital ghostbuster with a keyboard.

Now go forth and make something brilliant.

— Eidolon Team
