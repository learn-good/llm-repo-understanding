import os
from anthropic import AsyncAnthropic

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
assert ANTHROPIC_API_KEY, "\n\nANTHROPIC_API_KEY must be set as an evironment variable, e.g. `export ANTHROPIC_API_KEY=123abc123...`"

anthropic_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

