import argparse

from src.induction.config import load_config
from src.induction.induction import audit_clusters


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    if not audit_clusters(load_config(args.config))["passed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()

