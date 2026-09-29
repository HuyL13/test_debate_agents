import argparse

from src.induction.config import load_config
from src.induction.induction import induce_cluster_modes


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    induce_cluster_modes(load_config(args.config))


if __name__ == "__main__":
    main()

