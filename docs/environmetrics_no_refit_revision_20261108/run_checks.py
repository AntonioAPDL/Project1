#!/usr/bin/env python3
"""Bounded saved-output release checks; no fitting or prediction generation."""
import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import subprocess
import sys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--workflow-root',type=Path,default=Path(__file__).resolve().parents[2])
    parser.add_argument('--article-root',type=Path)
    parser.add_argument('--report-dir',type=Path,required=True)
    args=parser.parse_args()
    root=args.workflow_root.resolve()
    article=(args.article_root or root/'Evironmetrics---REVISED-DOC-Corrected-2').resolve()
    out=args.report_dir.resolve()
    if out.exists() or not out.is_relative_to(Path('/tmp')):
        parser.error('--report-dir must be a fresh directory under /tmp')
    out.mkdir(parents=True)
    records=[]
    def run(name,command,cwd=root):
        result=subprocess.run(command,cwd=cwd,text=True,stdout=subprocess.PIPE,stderr=subprocess.STDOUT)
        (out/(name+'.log')).write_text(result.stdout)
        count=re.search(r'Ran (\d+) tests?',result.stdout)
        records.append(dict(name=name,argv=list(map(str,command)),cwd=str(cwd),
                            returncode=result.returncode,python_tests=int(count[1]) if count else None))
        print(name+': '+('PASS' if result.returncode==0 else 'FAIL'),flush=True)
    py=sys.executable
    run('article_saved_output_release',[py,'-B',str(article/'scripts/no_refit_revision.py'),'--check'])
    run('article_saved_output_tests',[py,'-B','-m','unittest','discover','-s',str(article/'tests'),
                                     '-p','test_no_refit_revision.py','-v'])
    run('metadata_tests',[py,'-B','-m','unittest','discover','-s','tests/python',
                          '-p','test_no_refit_reporting_metadata.py','-v'])
    for name in ('test_no_refit_review_diagnostics.R','test_no_refit_diagnostic_indices.R',
                 'test_no_refit_synthesis_diagnostics.R'):
        run(name,['Rscript','--vanilla','-e',f'testthat::test_file("tests/testthat/{name}", '
                  'reporter="summary", stop_on_failure=TRUE, stop_on_warning=TRUE)'])
    run('metadata_bundle',[py,'-B',str(article/'artifacts/no_refit_revision/reporting/inputs/build_no_refit_reporting_metadata.py'),
                          '--output-dir',str(article/'artifacts/no_refit_revision/reporting'),'--check'])
    run('conditional_identities',[py,'-B',str(article/'artifacts/no_refit_revision/inference_scope/verify_conditional_identities.py')])
    run('synthesis_bundle',['Rscript','--vanilla',str(article/'artifacts/no_refit_revision/synthesis_diagnostics/reproduce/build_no_refit_synthesis_diagnostics.R'),
                            '--check','--output-dir',str(article/'artifacts/no_refit_revision/synthesis_diagnostics')])
    # Existing scripts retain their full protected-file and numerical contracts.
    run('preceding_revision_contracts',[py,'-B',str(root/'docs/environmetrics_comment2_revision_20261107/run_checks.py'),
        '--workflow-root',str(root),'--report-dir',str(out/'preceding_revision_contracts')])
    archived=article/'artifacts/no_refit_revision/reproduce'
    comparisons={}
    for rel in ('scripts/build_no_refit_review_diagnostics.R','R/environmetrics/no_refit_review_helpers.R',
                'config/no_refit_review_diagnostics.json'):
        live=hashlib.sha256((root/rel).read_bytes()).hexdigest()
        frozen=hashlib.sha256((archived/rel).read_bytes()).hexdigest()
        comparisons[rel]=dict(live=live,frozen=frozen,equal=live==frozen)
    (out/'executed_source_comparison.json').write_text(json.dumps(comparisons,indent=2)+'\n')
    summary=dict(created_utc=datetime.now(timezone.utc).isoformat(),workflow_root=str(root),
        article_root=str(article),commands=records,
        all_passed=all(r['returncode']==0 for r in records) and all(x['equal'] for x in comparisons.values()))
    (out/'summary.json').write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({'all_passed':summary['all_passed']},indent=2))
    return 0 if summary['all_passed'] else 1


if __name__=='__main__':
    raise SystemExit(main())
