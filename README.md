# Cashbuild Macro Layout Generator

This Streamlit MVP now works as a true Stage 1 macro generator. It generates one best rectangular macro layout for a Cashbuild-style building footprint, keeps the code beginner-friendly, and does not rely on databases, authentication, external APIs, or optimization libraries.

## How to install

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## How to run

```bash
streamlit run app.py
```

## What the MVP does

- Takes building width, building depth, entrance side, and service side as inputs.
- Converts millimetres to metres internally.
- Uses a simple four-screen Streamlit flow: Home, Stage 1 Macro Inputs, Stage 1 Macro Review, and a Stage 2 placeholder.
- Generates one best Stage 1 macro layout only.
- Draws only the macro zones: Trading Area, Admin Block, Goods Receiving, Yard, Off-loading Yard, and Parking.
- Keeps POS, door, and frontage logic available as metadata for validation and future Stage 2 detailing, but does not draw those detail elements on the Stage 1 macro plan.
- Tries to fit the full requested internal targets of 1250 m² Trading Area plus the macro internal support zones whenever the building can physically support them.
- Uses a fixed Cashbuild frontage opening sequence, 2400 mm opening clearances at the actual openings, and simple POS zones in the frontage gaps.
- Scores the macro layout on adjacency, access logic, clean proportions, non-overlap, and dominant trading floor.
- Draws the best macro layout with the building footprint, labels, area values, and validation results.
- Leaves a clean handoff for future Stage 2 micro-layout generation inside the internal macro zones.

For this MVP, the input width and depth describe the internal building footprint only. Trading Area, Admin Block, and Goods Receiving stay inside the building, while Yard, Off-loading Yard, and Parking are drawn outside the building on the service side. Frontage opening positions stay fixed in mm from the left inside wall of the entrance side.
