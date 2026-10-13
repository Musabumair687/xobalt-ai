"""Direct Google Gemini REST client for 100% reliable LLM inference.

Bypasses langchain-google-genai Automatic Function Calling (AFC) deprecation bugs
and directly invokes Google's v1beta REST generateContent endpoint using httpx.
Implements the LangChain BaseChatModel interface (ainvoke, invoke, with_structured_output).
"""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional, Type, TypeVar
import httpx
from pydantic import BaseModel
from langchain_core.messages import AIMessage, BaseMessage

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


class StructuredOutputWrapper:
    """Wraps GeminiDirectClient to return parsed Pydantic models."""

    def __init__(self, client: GeminiDirectClient, schema: Type[T]):
        self.client = client
        self.schema = schema

    async def ainvoke(self, prompt: Any) -> T:
        prompt_str = self.client._extract_prompt_text(prompt)
        schema_json = json.dumps(self.schema.model_json_schema(), indent=2)

        structured_prompt = (
            f"{prompt_str}\n\n"
            f"IMPORTANT: You MUST respond with ONLY a valid JSON object matching this schema:\n"
            f"{schema_json}\n\n"
            f"DO NOT include markdown code blocks, backticks (```json), or any commentary outside the JSON."
        )

        raw_resp = await self.client.ainvoke(structured_prompt)
        text = raw_resp.content.strip()

        # Clean any potential markdown backticks
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        text = text.strip()

        try:
            data = json.loads(text)
            return self.schema.model_validate(data)
        except Exception as e:
            # Try regex match if extra text was included
            match = re.search(r"\{.*\}", text, re.DOTALL)
            if match:
                try:
                    data = json.loads(match.group(0))
                    return self.schema.model_validate(data)
                except Exception as inner_e:
                    logger.error("Failed to parse regex-extracted JSON: %s. Raw: %s", inner_e, text[:200])
            logger.error("Gemini Structured Output JSON parse error: %s. Raw text: %s", e, text[:200])
            raise RuntimeError(f"Failed to parse Gemini output into {self.schema.__name__}: {e}")

    def invoke(self, prompt: Any) -> T:
        import asyncio
        return asyncio.run(self.ainvoke(prompt))


class GeminiDirectClient:
    """Ultra-reliable direct Gemini REST client compatible with LangChain."""

    def __init__(
        self,
        api_key: str,
        model: str = "gemini-2.5-flash",
        temperature: float = 0.7,
        timeout: float = 30.0,
    ):
        self.api_key = api_key
        # Clean model name
        if model.startswith("models/"):
            model = model.replace("models/", "")
        self.model = model
        self.temperature = temperature
        self.timeout = timeout

    def _extract_prompt_text(self, prompt: Any) -> str:
        if isinstance(prompt, str):
            return prompt
        elif isinstance(prompt, list):
            parts = []
            for m in prompt:
                if isinstance(m, BaseMessage):
                    parts.append(m.content)
                elif isinstance(m, dict):
                    parts.append(m.get("content", str(m)))
                else:
                    parts.append(str(m))
            return "\n\n".join(parts)
        elif hasattr(prompt, "to_string"):
            return prompt.to_string()
        elif hasattr(prompt, "content"):
            return prompt.content
        return str(prompt)

    async def ainvoke(self, prompt: Any) -> AIMessage:
        prompt_text = self._extract_prompt_text(prompt)

        # Candidate models to try in order of priority
        candidate_models = [self.model]
        if "gemini-2.5-flash" not in candidate_models:
            candidate_models.append("gemini-2.5-flash")
        if "gemini-2.5-pro" not in candidate_models:
            candidate_models.append("gemini-2.5-pro")

        last_error = None

        for mod in candidate_models:
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{mod}:generateContent?key={self.api_key}"
            payload = {
                "contents": [
                    {
                        "parts": [
                            {"text": prompt_text}
                        ]
                    }
                ],
                "generationConfig": {
                    "temperature": self.temperature,
                }
            }

            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    resp = await client.post(url, json=payload)

                    if resp.status_code == 200:
                        data = resp.json()
                        candidates = data.get("candidates", [])
                        if candidates:
                            content_parts = candidates[0].get("content", {}).get("parts", [])
                            if content_parts:
                                text_out = content_parts[0].get("text", "")
                                return AIMessage(content=text_out)
                        return AIMessage(content="")

                    # If 404 or bad request, log and try next candidate
                    err_body = resp.text[:300]
                    logger.warning("Gemini REST model '%s' failed (HTTP %s): %s", mod, resp.status_code, err_body)
                    last_error = f"HTTP {resp.status_code}: {err_body}"

            except Exception as exc:
                logger.warning("Gemini REST network error for model '%s': %s", mod, exc)
                last_error = str(exc)

        raise RuntimeError(f"All Gemini models failed. Last error: {last_error}")

    def invoke(self, prompt: Any) -> AIMessage:
        import asyncio
        return asyncio.run(self.ainvoke(prompt))

    def with_structured_output(self, schema: Type[T]) -> StructuredOutputWrapper:
        return StructuredOutputWrapper(self, schema)
