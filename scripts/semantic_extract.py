import argparse

from src.induction.config import load_config
from src.induction.data import load_positive_samples
from src.induction.semantic import extract_semantic_records
from src.llm.client import Client
from src.llm.config import ModelConfig
from src.io_utils import write_json


def main(argv=None):
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    parser.add_argument("--resume", action="store_true")
    args = parser.parse_args(argv)
    config = load_config(args.config)
    samples, stats = load_positive_samples(config)
    config.output_dir.mkdir(parents=True, exist_ok=True)
    write_json(config.output_dir / "data_stats.json", stats)
    for sample in samples:
        from src.io_utils import append_jsonl
        append_jsonl(config.output_dir / "positive_samples.jsonl", sample)
    model_name = __import__("os").environ.get(config.model_env, "configured-model")
    model = ModelConfig(name=model_name, temperature=config.llm_temperature,
                        max_attempts=config.llm_max_retries)
    client = Client(model, config.output_dir / "llm_cache.sqlite3",
                    config.output_dir / "audit" / "api_calls.jsonl")
    extract_semantic_records(config, samples, client, resume=args.resume)


if __name__ == "__main__":
    main()

