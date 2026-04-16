# Cashbuild Layout Generator MVP

This Streamlit MVP generates three simple rectangular layout options for a Cashbuild-style building footprint. It uses hard adjacency and boundary rules, keeps the code beginner-friendly, and does not rely on databases, authentication, external APIs, or optimization libraries.

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
- Generates three different 2D rectangular layout options.
- Tries to fit the full requested internal targets of 1250 m² Trading Area and 130 m² Offices whenever the building can physically support them.
- Scores and sorts the options from best to worst.
- Draws each option with the building footprint, labels, area values, and validation results.

For this MVP, the input width and depth describe the internal building footprint only. Trading Area and Offices stay inside the building, while Yard and Off-loading Yard are drawn outside the building on the service side.
