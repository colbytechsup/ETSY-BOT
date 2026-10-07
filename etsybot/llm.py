"""LLM backends. StubLLM is offline and deterministic; AnthropicLLM is optional."""
import os


class StubLLM:
    """Returns the caller-supplied fallback, so the sim runs with no API key."""

    def complete(self, prompt: str, fallback: str = "") -> str:
        return fallback


class AnthropicLLM:
    """Needs `pip install anthropic` and ANTHROPIC_API_KEY. Set ETSYBOT_MODEL."""

    def __init__(self):
        import anthropic  # imported lazily so the sim works without it

        self.client = anthropic.Anthropic()
        self.model = os.environ["ETSYBOT_MODEL"]

    def complete(self, prompt: str, fallback: str = "") -> str:
        msg = self.client.messages.create(
            model=self.model,
            max_tokens=300,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip() or fallback


def make_llm(use_api: bool):
    return AnthropicLLM() if use_api else StubLLM()
