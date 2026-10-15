"""Build an upload bundle from an explicit allowlist; never include credentials."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED

ROOT = Path(__file__).resolve().parents[1]


def main():
    output = ROOT / 'outputs/courtroom-kaggle.zip'
    output.parent.mkdir(exist_ok=True)
    files = []
    for folder in ('src', 'configs', 'definitions', 'data/cocolofa/classification', 'data/dev_classification_errors'):
        files.extend(p for p in (ROOT / folder).rglob('*')
                     if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc')
    files.extend(ROOT / name for name in (
        'requirements-kaggle.txt', 'scripts/check_kaggle_gpu.py', 'docs/action-centric-v4.md', 'cache/courtroom_rl/llama3_tokenizer.json',
        'docs/kaggle-training.ipynb', 'docs/kaggle-training.md',
        'docs/diagnostics/resume-source-migrations.json'))
    with ZipFile(output, 'w', ZIP_DEFLATED) as archive:
        for path in sorted(files):
            if not path.is_file():
                raise FileNotFoundError(path)
            if path.name in ('.env', 'key.txt'):
                raise ValueError('Credentials cannot be packaged')
            archive.write(path, 'cocolofa_pard/' + path.relative_to(ROOT).as_posix())
    print(f'{output} ({output.stat().st_size / 1024**2:.1f} MiB); no .env, key.txt or runs')


if __name__ == '__main__':
    main()
