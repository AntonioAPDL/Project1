#!/usr/bin/env python3
"""Validate the active Corrected-3 article without fitting or changing archives.

Historical campaign wrappers remain frozen. This is the active combined entrypoint
and passes the selected article root to every check and dataset-aware test.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys

WORKFLOW = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKFLOW/'scripts'))
from article_repository_binding import assert_article_write_target


def main() -> int:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workflow-root',type=Path,default=WORKFLOW)
    parser.add_argument('--article-root',type=Path)
    parser.add_argument('--corrections-root',type=Path)
    parser.add_argument('--public-root',type=Path)
    parser.add_argument('--he3-runtime-root',type=Path)
    parser.add_argument('--report-dir',type=Path,required=True)
    args=parser.parse_args()
    root=args.workflow_root.resolve()
    article=assert_article_write_target(args.article_root,root)
    response=(args.corrections_root or root.parent/'Corrections---Project-1').resolve()
    public=(args.public_root or root.parent/'san-lorenzo-exdqlm-reproducibility').resolve()
    he3=(args.he3_runtime_root or root.parent/'project1_ucsc_phd_runtime/multimodel_v8_he3_exdqlm_ablation_current_authority_20260625').resolve()
    out=args.report_dir.resolve()
    if out.exists() or not out.is_relative_to(Path('/tmp')):
        parser.error('--report-dir must be a fresh directory under /tmp')
    out.mkdir(parents=True)
    env=os.environ.copy()
    env.update(ENVIRONMETRICS_ARTICLE_ROOT=str(article),
        NO_REFIT_REPORTING_DIR=str(article/'artifacts/no_refit_revision/reporting'),
        NO_REFIT_RESULT_DIR=str(article/'artifacts/no_refit_revision/results'),
        NO_REFIT_SYNTHESIS_DIR=str(article/'artifacts/no_refit_revision/synthesis_diagnostics'))
    for key in ('NO_REFIT_REPORTING_DIR','NO_REFIT_RESULT_DIR','NO_REFIT_SYNTHESIS_DIR'):
        if not Path(env[key]).is_dir():
            parser.error('Required active-article dataset is missing: '+key)
    records=[]
    py=sys.executable

    def run(name,command,cwd=root):
        command=list(map(str,command))
        result=subprocess.run(command,cwd=cwd,env=env,text=True,
            stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (out/(name+'.log')).write_text(result.stdout)
        count=re.search(r'Ran (\d+) tests?',result.stdout)
        skip=re.search(r'(?:\bskipped=\d+|\bSKIPPED\b|══ Skipped|── .*Skip)',result.stdout)
        records.append(dict(name=name,argv=command,cwd=str(cwd),returncode=result.returncode,
            python_tests=int(count[1]) if count else 0,unexpected_skip=bool(skip)))
        print(name+': '+('PASS' if result.returncode==0 and not skip else 'FAIL'),flush=True)

    for pattern in ('test_r1_overview_contract.py','test_r1_m1_uncertainty_contract.py',
        'test_he1_runtime_contract.py','test_he6_forecast_design_contract.py',
        'test_he7_latest_forecast_issue_contract.py','test_reviewer1_remaining_contracts.py',
        'test_article_legacy_uppercase_figures_sync.py','test_comment1_figure_render_guards.py',
        'test_comment2_component_diagnostics.py','test_no_refit_reporting_metadata.py',
        'test_article_repository_binding.py','test_article_repository_migration_verification.py',
        'test_article_asset_review_benchmark_source.py',
        'test_exal_m_t1_setup_support_fullhistory_contract.py',
        'test_revised_article_stage1_refresh_contract.py',
        'test_software_availability_contract.py',
        'test_he3_exdqlm_ablation_tooling.py','test_nmt1_static_parity.py'):
        run(pattern[:-3],[py,'-B','-m','unittest','discover','-s','tests/python','-p',pattern,'-v'])
    for pattern in ('test_article_a1_and_table_contracts.py','test_manuscript_text_contract.py',
        'test_comment1_figure_revision.py','test_comment2_revision.py','test_no_refit_revision.py'):
        run(pattern[:-3],[py,'-B','-m','unittest','discover','-s',article/'tests','-p',pattern,'-v'])
    r_counts={}
    for name in ('test_post_publication_figures.R','test_comment2_external_baselines.R',
        'test_no_refit_review_diagnostics.R','test_no_refit_diagnostic_indices.R',
        'test_no_refit_synthesis_diagnostics.R'):
        run(name,['Rscript','--vanilla','-e',f'testthat::test_file("tests/testthat/{name}", '
            'reporter="summary", stop_on_failure=TRUE, stop_on_warning=TRUE)'])
        log=(out/(name+'.log')).read_text()
        match=re.search(re.escape(name.removeprefix('test_').removesuffix('.R'))+r': (\.+)',log)
        r_counts[name]=len(match[1]) if match else None
    for script in ('comment1_figure_revision.py','comment2_revision.py','no_refit_revision.py'):
        run(script,[py,'-B',article/'scripts'/script,'--article-root',article,'--check'])
    run('figure_paths',[py,'-B',article/'scripts/validate_manuscript_figure_paths.py','--article-root',article])
    run('output_lineage',[py,'-B',article/'scripts/validate_authoritative_output_lineage.py',
        '--article-root',article,'--corrections-root',response,'--report-dir',out/'lineage'])
    run('publication_freeze',[py,'-B',root/'scripts/validate_publication_freeze.py',
        '--workflow-root',root,'--article-root',article,'--corrections-root',response,
        '--he3-runtime-root',he3,'--report-dir',out/'publication_freeze'])
    run('cross_repo_wiring',[py,'-B',root/'scripts/validate_revision_cross_repo_wiring.py',
        '--workflow-root',root,'--article-root',article,'--corrections-root',response,
        '--output-dir',out/'cross_repo','--check-only','--strict'])
    for phase,baseline in (
        ('comment1','docs/environmetrics_comment1_plan_20261107/readiness/baseline_snapshot.json'),
        ('comment2','docs/environmetrics_comment2_revision_20261107/preparation/baseline_snapshot.json')):
        run(phase+'_preservation',[py,'-B',root/'docs/environmetrics_comment1_plan_20261107/readiness/audit_readiness.py',
            '--workflow-root',root,'--article-root',article,'--response-root',response,'--public-root',public,
            '--compare',root/baseline,'--out',out/(phase+'_preservation.json')])
    run('metadata_bundle',[py,'-B',article/'artifacts/no_refit_revision/reporting/inputs/build_no_refit_reporting_metadata.py',
        '--output-dir',article/'artifacts/no_refit_revision/reporting','--check'])
    run('conditional_identities',[py,'-B',article/'artifacts/no_refit_revision/inference_scope/verify_conditional_identities.py'])
    run('synthesis_bundle',['Rscript','--vanilla',article/'artifacts/no_refit_revision/synthesis_diagnostics/reproduce/build_no_refit_synthesis_diagnostics.R',
        '--output-dir',article/'artifacts/no_refit_revision/synthesis_diagnostics','--check'])
    comparisons={}
    for subtree,rel in (
        ('comment2_revision','scripts/build_comment2_external_baselines.R'),
        ('comment2_revision','config/comment2_external_baselines.json'),
        ('comment2_revision','scripts/audit_comment2_component_diagnostics.py'),
        ('no_refit_revision','scripts/build_no_refit_review_diagnostics.R'),
        ('no_refit_revision','R/environmetrics/no_refit_review_helpers.R'),
        ('no_refit_revision','config/no_refit_review_diagnostics.json')):
        live=hashlib.sha256((root/rel).read_bytes()).hexdigest()
        frozen=hashlib.sha256((article/'artifacts'/subtree/'reproduce'/rel).read_bytes()).hexdigest()
        comparisons[rel]=dict(live=live,frozen=frozen,equal=live==frozen)
    (out/'source_archive_comparisons.json').write_text(json.dumps(comparisons,indent=2)+'\n')
    summary=dict(created_utc=datetime.now(timezone.utc).isoformat(),workflow_root=str(root),
        article_root=str(article),dataset_environment={key:env[key] for key in ('ENVIRONMETRICS_ARTICLE_ROOT',
        'NO_REFIT_REPORTING_DIR','NO_REFIT_RESULT_DIR','NO_REFIT_SYNTHESIS_DIR')},commands=records,
        python_tests=sum(r['python_tests'] for r in records),r_assertions=r_counts,
        all_passed=all(r['returncode']==0 and not r['unexpected_skip'] for r in records)
                   and all(r['equal'] for r in comparisons.values()))
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({k:summary[k] for k in ('python_tests','r_assertions','all_passed')},indent=2))
    return 0 if summary['all_passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
