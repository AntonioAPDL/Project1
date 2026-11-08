This package is an audit and proposed plan, not an implemented manuscript revision.

Start with refinement_20261108/IMPLEMENTATION_PLAN.txt for the current execution
plan. Its execution_contract.json fixes estimator, quantile, schema, optional-stop
and release rules; decisions.json explains the justified refinements. The updated
task_register.json preserves the original 17 task IDs with concrete dependencies.

PLAN.txt remains the detailed original investigation. reviewer_matrix.json maps
the referee requests to work feasible now and later computation. The full initial
package is preserved under history/initial_plan_v1/ with its original checksums.
Evidence contains the read-only investigations and inventory of saved forecasts.

Authority: article main 2583ee41c1367e65d4d71ed36cf280a4f555a513;
workflow main f69d4c8ac144f405b3535c4d8c8015cc8af9e2db.

No model fits or new posterior simulations were launched. No manuscript, fitting
code, configuration, selected prediction, original score, or figure was changed.
The only new repository files are this planning package. Read-only calculations
verified that the existing prediction caches reproduce the published scores.

The proposed immediate phase uses current fits as its fixed evidence base and
adds reporting corrections and verification from already saved distributions.
New likelihoods, model retuning, and posterior-method comparisons remain later
work. The completed first-comment structure and second-comment additions stay
in place. Numerical results for proposed new diagnostics do not yet exist here.

The November 8 refinement was independently reviewed for scoring/calibration,
effects/settings and model/inference. It changes planning documents only. The
existing score-replay script remains runnable using REPLAY.txt; proposed production
diagnostic/generation scripts named in the new plan have not been implemented.
