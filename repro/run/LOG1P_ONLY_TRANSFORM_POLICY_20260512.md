# Log1p-Only Transform Policy

Date: 2026-05-12

## Purpose

This note freezes the current workflow decision that all active HE2 relaunch work must use `log1p_cms` and must not use `log_log1p_cms`.

This is a scientific and workflow-safety rule, not a plotting preference.

## Required contract

For current relaunch work:

- retrospective observations must be stored and consumed on `log1p_cms`
- forecast ensembles must be adapted and consumed on `log1p_cms`
- fit internals must stay on `log1p_cms`
- post internals must stay on `log1p_cms`
- figures and tables should report the same scale explicitly

## What was wrong before

The recent HE2 relaunch path was mixed:

- retros were stored as `log1p_cms`
- some legacy bridge code applied an extra `log()` to those already-logged values
- the config contract still advertised `analysis_scale_* = log_log1p_cms`

That created a sensitive mismatch between storage scale and model-internal scale.

## Current enforcement

The current workflow now enforces:

- `scale_contract.legacy_fit_input_scale = log1p_cms`
- `scale_contract.legacy_post_input_scale = log1p_cms`
- `scale_contract.analysis_scale_fit_internal = log1p_cms`
- `scale_contract.analysis_scale_post_internal = log1p_cms`

Current config validation must reject `log_log*` internal scales for active relaunch configs.

## Scope

This policy is required for:

- the HE2 Bayesian publication relaunch flow
- the current `exdqlm_multivar_keep` all-cutoff rollout
- the current repaired q35 path
- follow-on propagation work for the remaining model families

Archived legacy configs and historical notes may still mention `log_log1p_cms`, but they are not acceptable as active run contracts.
