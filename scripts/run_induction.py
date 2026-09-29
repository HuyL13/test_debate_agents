import argparse

from src.induction.config import load_config
from src.induction.pipeline import run_induction


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    run_induction(load_config(args.config), resume=args.resume)


if __name__ == "__main__":
    main()

