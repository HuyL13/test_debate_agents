"""Supervise frozen full-test runs; publish scores only after complete coverage."""
import argparse
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from src.io_utils import write_json
from src.runner import evaluate_run


def read(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def completed(directory):
    return sum(read(p).get('status') == 'ok' for p in (directory / 'samples').glob('*.json'))


def render(jobs, destination):
    paper = read(ROOT / 'reports/cocolofa_paper_baselines.json')
    lines = ['# CoCoLoFa full-test comparison', '',
             'Updated UTC: ' + datetime.now(timezone.utc).isoformat(), '',
             'Published baselines: [CoCoLoFa paper, Tables 4 and 5](' + paper['source'] + '). '
             'These are published numbers, not baseline reruns. All scores below are percentages.', '',
             '| Method | Detection P | Detection R | Detection F1 | Classification P | Classification R | Classification macro-F1 |',
             '|---|---:|---:|---:|---:|---:|---:|']
    for row in paper['rows']:
        lines.append('| ' + row['method'] + ' (paper) | ' + ' | '.join(map(str, row['values'])) + ' |')
    for mode in ('single', 'adaptive'):
        values = []
        for task in ('detection', 'classification'):
            job = next(j for j in jobs if j['task'] == task and j['mode'] == mode)
            result = job.get('result')
            if result is None:
                values += ['pending'] * 3
            elif task == 'detection':
                values += [f"{100 * result[k]:.2f}" for k in ('precision', 'recall', 'f1')]
            else:
                values += [f"{100 * sum(c[k] for c in result['per_class'].values()) / 8:.2f}"
                           for k in ('precision', 'recall')]
                values += [f"{100 * result['macro_f1']:.2f}"]
        lines.append('| gpt-oss-20b / ' + mode + ' (this repo) | ' + ' | '.join(values) + ' |')
    lines += ['', '## Run status', '', '| Run | Completed / required | State | Launches |', '|---|---:|---|---:|']
    for job in jobs:
        lines.append(f"| {job['task']} / {job['mode']} | {job['completed']} / {job['expected']} | "
                     f"{job['state']} | {job['launches']} |")
    lines += ['', '## Evaluation conditions', '',
              '- Full original test split: detection 798 comments; classification 481 gold-positive comments, independently selected.',
              '- Frozen source, prompts, data hashes and configs; no prompt or model selection from test outcomes.',
              '- NVIDIA openai/gpt-oss-20b, temperature 1, max output 4096; title + immediate same-article parent + target.',
              '- Single and PARD-inspired adaptive are new methods, not reproductions of the paper models. Adaptive budget is at most 3 rounds.',
              '- Detection uses positive-class P/R/F1. Classification uses unweighted macro P/R/F1 across all eight labels; paper explicitly specifies macro-F1, but its exact P/R averaging implementation is unavailable.',
              '- Different models, prompting and training regimes: this table is descriptive, not a controlled claim of architectural superiority. One stochastic run per method; no significance claim.',
              '- One broken test parent reference is left empty and the comment is retained, as documented in UPSTREAM_AUDIT.md.',
              '- Pending or failed runs have no score. Final scores require full ID coverage and manifest validation.',
              '- The computer must remain awake with network access. Raw logs and per-sample checkpoints are in outputs/full-test-v1/.', '']
    temporary = destination.with_suffix('.md.tmp')
    temporary.write_text('\n'.join(lines), encoding='utf-8')
    temporary.replace(destination)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare-only', action='store_true')
    args = parser.parse_args()
    os.chdir(ROOT)
    directory = ROOT / 'outputs/full-test-v1'
    directory.mkdir(parents=True, exist_ok=True)
    lock = directory / 'supervisor.lock'
    if not args.prepare_only:
        # Exclusive creation prevents two supervisors writing the same runs.
        with lock.open('x') as stream:
            stream.write(str(os.getpid()))
    jobs = []
    active = {}
    try:
        for task in ('detection', 'classification'):
            for mode in ('single', 'adaptive'):
                name = task + '-' + mode
                jobs.append({'task': task, 'mode': mode, 'name': name,
                             'output': str(directory / name), 'expected': 798 if task == 'detection' else 481,
                             'completed': 0, 'state': 'queued', 'launches': 0, 'no_progress': 0})
        while True:
            for job in jobs:
                output = Path(job['output'])
                job['completed'] = completed(output)
                name = job['name']
                if name in active:
                    process, log = active[name]
                    if process.poll() is None:
                        continue
                    log.close()
                    del active[name]
                    job['last_exit_code'] = process.returncode
                    if process.returncode == 0:
                        result = evaluate_run(output / 'predictions.jsonl')
                        if result['count'] != job['expected'] or result['selection_scope'] != 'full_split':
                            raise ValueError('Incomplete coverage at completion')
                        job.update(state='complete', result=result)
                        continue
                    job['no_progress'] = (job['no_progress'] + 1 if job['completed'] <= job['before_launch'] else 0)
                    job['state'] = 'blocked' if job['no_progress'] >= 3 or job['launches'] >= 100 else 'queued'
                if args.prepare_only or job['state'] in ('complete', 'blocked'):
                    continue
                summary = output / 'summary.json'
                if summary.exists() and read(summary).get('status') == 'complete':
                    result = evaluate_run(output / 'predictions.jsonl')
                    if result['count'] != job['expected'] or result['selection_scope'] != 'full_split':
                        raise ValueError('Existing run is not full test coverage')
                    job.update(state='complete', result=result)
                    continue
                command = [sys.executable, '-u', '-m', 'src.run_' + job['task'],
                           '--config', f'configs/full-{name}.yaml', '--split', 'test',
                           '--frozen', f'reports/frozen-full-{name}-v1.json', '--output', str(output)]
                if (output / 'manifest.json').exists():
                    command.append('--resume')
                log = (directory / (name + '.console.log')).open('a', encoding='utf-8')
                process = subprocess.Popen(command, stdout=log, stderr=subprocess.STDOUT, cwd=ROOT)
                active[name] = (process, log)
                job.update(state='running', pid=process.pid, launches=job['launches'] + 1,
                           before_launch=job['completed'])
            render(jobs, ROOT / 'reports/FULL_TEST_COMPARISON.md')
            write_json(directory / 'status.json', {'updated_at': datetime.now(timezone.utc).isoformat(),
                                                 'supervisor_pid': os.getpid(), 'jobs': jobs})
            if args.prepare_only or all(j['state'] in ('complete', 'blocked') for j in jobs):
                break
            time.sleep(30)
    finally:
        for process, log in active.values():
            process.terminate()
            process.wait()
            log.close()
        if not args.prepare_only:
            lock.unlink(missing_ok=True)
    return 0 if args.prepare_only or all(j['state'] == 'complete' for j in jobs) else 1


if __name__ == '__main__':
    raise SystemExit(main())
