import argparse

import numpy as np

from src.induction.clustering import search_k
from src.induction.config import load_config
from src.io_utils import read_jsonl


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    config = load_config(args.config)
    records = read_jsonl(config.output_dir / "semantic_records.jsonl")
    embeddings = np.load(config.output_dir / "canonical_embeddings.npy")
    search_k(config, embeddings, records)


if __name__ == "__main__":
    main()

