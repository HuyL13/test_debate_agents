from typing import Protocol


class LLM(Protocol):
    def generate(self, *, system_prompt: str, user_prompt: str, schema: dict,
                 metadata: dict, validator=None) -> dict: ...
