# Cashbuild Generator - Agent Instructions

## Project goal
Build a simple rule-based layout generator for Cashbuild-type stores.

## Current scope
This MVP generates 2D rectangular layout options for:
- Trading Area
- Offices
- Yard
- Off-loading Yard

Shop width and depth represent the internal building footprint only.

- Trading Area and Offices are internal
- Yard and Off-loading Yard are external

## Tech stack
- Python
- Streamlit
- matplotlib

## Code style
- Keep code simple
- Keep code beginner-friendly
- Add comments for important logic
- Prefer readability over cleverness
- Keep functions modular and easy to understand

## Geometry / layout rules
- Use rectangle-based layouts only
- Use metres internally
- Keep deterministic templates unless explicitly asked otherwise
- Do not introduce optimization libraries unless approved
- Do not use shapely unless explicitly approved

## Workflow
- Use Plan mode for major architecture changes
- Use normal mode for small targeted fixes
- Ask before changing core assumptions
- Preserve working features when making changes

## Product priorities
- Prioritize believable architectural layout logic
- Prioritize clear validation and scoring
- Keep the app easy to test in the browser
- Do not add unnecessary complexity too early

## File structure
Keep the current structure unless explicitly asked to change it:
- app.py
- layout_engine.py
- constraints.py
- drawing.py
- requirements.txt
- README.md
- AGENTS.md