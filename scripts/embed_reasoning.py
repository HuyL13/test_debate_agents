import argparse

from src.induction.config import load_config
from src.induction.embedding import embed_reasoning


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    embed_reasoning(load_config(args.config))


if __name__ == "__main__":
    main()

