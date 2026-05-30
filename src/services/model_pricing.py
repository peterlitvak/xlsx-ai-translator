"""OpenAI model pricing used for translation cost estimates."""

# Standard API text-token prices in USD per 1K tokens.
# Source: OpenAI API model pricing pages, checked May 29, 2026.
MODEL_PRICING = {
    "gpt-4o": {"input": 0.0025, "output": 0.01},
    "gpt-4o-mini": {"input": 0.00015, "output": 0.0006},
}
