import argparse

from src.induction.config import load_config
from src.induction.induction import induce_definition


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    induce_definition(load_config(args.config))


if __name__ == "__main__":
    main()

