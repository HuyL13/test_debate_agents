import argparse

from src.induction.audit import audit_semantics
from src.induction.config import load_config


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    result = audit_semantics(load_config(args.config))
    if not result["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

