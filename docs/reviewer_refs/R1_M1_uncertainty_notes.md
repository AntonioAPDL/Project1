# R1-M1 Notes: Uncertainty Framing for the Introduction

## Source
Panchanathan, A., Ahrari, A., Ghag, K. S., Mustafa, S., Haghighi, A. T., Klöve, B., and Oussalah, M. (2024). *An overview of approaches for reducing uncertainties in hydrological forecasting: Progress and challenges*. Earth-Science Reviews, 258, 104956. https://doi.org/10.1016/j.earscirev.2024.104956

PDF on server:
- `docs/reviewer_refs/Panchanathan_et_al_2024.pdf`

## Distilled points from the review
The review frames uncertainty in hydrological forecasting around the reliability of data, the adequacy of model conceptualization, the quality of calibration/validation, and the accuracy of predictions.

Useful categories for our paper:
- `measurement uncertainty`: errors in observed or instrument-derived quantities
- `input uncertainty`: inaccuracies in forcings or external inputs, including interpolation, scaling, and forecast deficiencies
- `initial-condition uncertainty`: uncertainty in the model state at forecast issuance
- `parameter uncertainty`: uncertainty from calibration, parameterization, and observation error
- `conceptual / structural uncertainty`: imperfect representation of hydrological processes and model structure
- `forecast uncertainty`: the downstream combination of the above uncertainty sources in the final predictive output

A second useful idea in the review is the workflow split:
- `Stage I`: input preparation and preprocessing
- `Stage II`: model conceptualization and setup
- `Stage III`: calibration and validation

This is helpful for Reviewer 1 because it gives a clean way to separate uncertainty sources before introducing the Bayesian framework.

## Tailored framing for this manuscript
For our paper, the most useful distinction is:

### 1. Meteorological uncertainty
This enters through atmospheric forcings and forecast generation. In our setting, this includes uncertainty carried by the forecast products themselves, such as precipitation forecasts, soil-moisture-related forecast covariates, and the ensemble forecast products delivered by ECMWF/GloFAS and NOAA/NWM.

### 2. Hydrological uncertainty
This enters through the translation from those inputs and products into river-flow behavior. In our setting, this includes uncertainty related to streamflow response, latent-state evolution, structural simplifications, parameterization, initial conditions, and the mismatch between retrospective products and observed discharge.

### 3. Observation / product mismatch uncertainty
For this paper, one additional distinction is important: observed discharge, retrospective analyses, and forecast products are not interchangeable measurements of the same object. Their discrepancies are part of the forecasting problem itself. This is precisely the part our correction-and-synthesis framework is designed to learn.

## What Reviewer 1 is right about
The original introduction moved too quickly between hydrological forecasting in general and specific meteorological-ensemble issues. That makes the motivation look less focused than it should be.

The cleaner structure is:
1. state that hydrological forecasting inherits multiple uncertainty layers;
2. distinguish meteorological uncertainty from hydrological uncertainty;
3. explain that operational streamflow products still require statistical correction because forecast products, retrospective products, and observations do not align perfectly;
4. only then introduce the Bayesian quantile-based correction-and-synthesis framework.

## Scope statement we should keep clear
This paper is not about generating meteorological ensembles. It starts from forecast and retrospective products that already exist and develops a Bayesian quantile-based framework for correcting and synthesizing them into probabilistic river-flow forecasts.

## Draft manuscript-side wording
Hydrological forecasting combines multiple layers of uncertainty. Part of that uncertainty enters upstream, through meteorological forcings and forecast generation. Another part enters downstream, through hydrological response, model structure, parameterization, initial conditions, and observation-related discrepancies. In operational river-flow forecasting, these layers are intertwined but not identical, and they should be distinguished conceptually.

In this work, we do not study how meteorological ensembles are generated. Instead, we start from forecast and retrospective streamflow products that are already available from forecasting centers and ask how they can be statistically corrected and synthesized for probabilistic river-flow forecasting at the site of interest. This is the role of the Bayesian quantile-based framework proposed in the paper.

## Implication for the response letter
The response to Reviewer 1 should say that the introduction was reorganized to:
- separate meteorological and hydrological uncertainty explicitly;
- avoid mixing atmospheric ensemble-generation details with hydrological motivation too early;
- position the paper as a probabilistic correction-and-synthesis contribution built on available forecast products.
