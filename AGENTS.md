# AGENTS.md — Food Demand Analysis

## Project purpose
Analyze weekly meal demand for an anonymized meal-delivery company to support purchasing, reduce waste/stockouts, and evaluate promotional associations.

## Data
- `data/raw/train.csv`: historical rows with `num_orders`.
- `data/raw/test.csv`: later weeks without `num_orders`.
- `data/raw/meal_info.csv`: meal category and cuisine.
- `data/raw/fulfilment_center_info.csv`: center type and operating area.
- Source files must remain unchanged and must not be committed to GitHub.

## Working rules
1. Use reproducible Python and explicit merge keys; validate many-to-one joins.
2. Print/check row counts and order sums before and after merges.
3. Do not silently remove outliers or fill absent center-meal-week rows with zero.
4. Every number in the client report must be reproducible from a notebook or generated table.
5. Correlation and observational promotion comparisons do not establish causation; include limitations.
6. Separate exploratory results from recommendations and state the KPI for each recommendation.
7. Use fixed random seeds for sampling and model comparisons.
8. Keep charts readable, titled with a finding, and save PNGs under `reports/figures/`.
9. Do not commit secrets, environment files, or source data.
