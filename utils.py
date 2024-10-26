import os
from anthropic import AsyncAnthropic
from typing import List, Tuple, Optional, Dict
import logging
from custom_logging import get_logger_with_level
import re

log = get_logger_with_level( logging.INFO ) # change logging level if the output is too verbose

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
    # Match both simple tags and tags with attributes
    opening_pattern = f"<{tag}[^>]*>"
    closing_tag = f"</{tag}>"
    
    opening_match = re.search(opening_pattern, response)
    
    if not (opening_match and closing_tag in response):
        log.warning("Unable to extract information for given tag (LLM likely did not follow response formatting instructions). Returning full response")
        return response
    else:
        start_index = opening_match.end()
        end_index = response.find(closing_tag, start_index)
        content = response[start_index:end_index]
        return content.strip()

def read_file_to_text(filepath: str) -> str:
    try:
        with open(filepath, 'r') as f:
            text = f.read()
    except Exception as e:
        raise IOError(f"Error reading file {filepath}: {e}")   
    return text

def replace_placeholders(text: str, replacements: Dict[str, str]) -> str:
    """Replace placeholders in instruction and user input templates"""
    for key, value in replacements.items():
        text = text.replace(key, value)
    return text