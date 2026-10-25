---
name: promotion-impact
description: Analyze observed association between email/homepage promotions and meal orders, controlling the comparison by center-meal pair where possible.
---

# Promotion impact analysis

## Trigger
Use when asked whether email promotions or homepage featuring are associated with order volume.

## Procedure
1. Verify the promotion flags are binary and inspect their prevalence.
2. Compare only center-meal pairs that have both promotion and non-promotion observations.
3. Report group sample sizes, means/medians, relative difference, Mann–Whitney U statistic, and p-value.
4. Explain that statistical significance is not causal proof.
5. Check potential confounding by checkout price, discount rate, week, meal, and center.
6. Save results to `reports/promotion_tests.csv` and chart to `reports/figures/`.

## Do not
- Claim that promotion caused an increase from observational data.
- Omit the comparison population or p-value.
- Treat email and homepage indicators as mutually exclusive.
