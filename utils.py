import os
from anthropic import AsyncAnthropic
from typing import List, Tuple, Optional
import logging
from custom_logging import get_logger_with_level

log = get_logger_with_level( logging.WARNING ) # change logging level if the output is too verbose

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY")
assert ANTHROPIC_API_KEY, "\n\nANTHROPIC_API_KEY must be set as an evironment variable, e.g. `export ANTHROPIC_API_KEY=123abc123...`"

anthropic_client = AsyncAnthropic(api_key=ANTHROPIC_API_KEY)

async def request_chat_completion(
    msgs: List[Tuple[str,str]], 
    model: str = "claude-3-5-sonnet-latest",
    temperature: int = 0,
    max_tokens: int = 8192,
)-> Optional[str]:
    """Request exam guide enhancement chat completion"""
    messages = [{"role": role, "content": msg_content} for role, msg_content in msgs]
    try:
        completion = await anthropic_client.messages.create(
            messages=messages,
            model="claude-3-5-sonnet-latest",
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = completion.content[0].text
    except Exception as e:
        model_provider = "Anthropic"
        log.error(f"Error while requesting {model_provider} chat completion: {e}")
        raise e
    return str(content)


def extract_xml(response: str, tag: str):
    opening_tag = f"<{tag}>"
    closing_tag = f"</{tag}>"
    if not (opening_tag in response and closing_tag in response):
        log.warning("Unable to extract information for given tag (LLM likely did not follow response formatting instructions). Returning full response")
        return response
    else:
        start_index = response.find(opening_tag) + len(opening_tag)
        end_index = response.find(closing_tag, start_index)
        content = response[start_index:end_index]
        return content.strip()