"""Interchangeable decision-model clients for a controlled benchmark."""

import json
import os
import urllib.error
import urllib.request
from typing import Any, Protocol


class ModelClient(Protocol):
    def chat(self, messages: list[dict[str, str]], schema: dict[str, Any]) -> dict[str, Any]: ...

    def embed(self, text: str) -> list[float] | None: ...

    def metadata(self) -> dict[str, str]: ...


class OllamaClient:
    def __init__(self, base_url: str, model: str, embedding_model: str) -> None:
        self.base_url, self.model, self.embedding_model = base_url.rstrip("/"), model, embedding_model

    def _post(self, route: str, payload: dict[str, Any]) -> dict[str, Any]:
        request = urllib.request.Request(f"{self.base_url}{route}", data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"}, method="POST")
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                return json.loads(response.read().decode("utf-8"))
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Cannot reach Ollama at {self.base_url}: {exc}") from exc

    def chat(self, messages: list[dict[str, str]], schema: dict[str, Any]) -> dict[str, Any]:
        result = self._post("/api/chat", {"model": self.model, "messages": messages, "stream": False, "format": schema, "think": False, "options": {"temperature": 0.1}})
        try:
            return json.loads(result.get("message", {}).get("content", ""))
        except json.JSONDecodeError as exc:
            raise RuntimeError("Ollama returned invalid JSON") from exc

    def embed(self, text: str) -> list[float] | None:
        try:
            return self._post("/api/embed", {"model": self.embedding_model, "input": text}).get("embeddings", [None])[0]
        except RuntimeError:
            return None

    def metadata(self) -> dict[str, str]:
        return {"provider": "ollama", "model": self.model, "embedding_model": self.embedding_model}


class OpenAIResponsesClient:
    """Responses-API client using JSON mode and application-side schema checks."""

    def __init__(self, api_key: str, model: str, retrieval: OllamaClient) -> None:
        if not api_key or not model:
            raise RuntimeError("MODEL_PROVIDER=openai requires OPENAI_API_KEY and OPENAI_MODEL")
        self.api_key, self.model, self.retrieval = api_key, model, retrieval

    def chat(self, messages: list[dict[str, str]], schema: dict[str, Any]) -> dict[str, Any]:
        # The experiment's action schema intentionally permits arbitrary tool
        # argument objects. JSON mode preserves that common interface across
        # providers; the application still parses and validates the result.
        payload = {"model": self.model, "input": messages, "store": False, "temperature": 0.1, "text": {"format": {"type": "json_object"}}}
        request = urllib.request.Request(
            "https://api.openai.com/v1/responses",
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(request, timeout=180) as response:
                result = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            raise RuntimeError(f"OpenAI Responses API returned HTTP {exc.code}: {exc.read().decode('utf-8', errors='replace')[:500]}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"Cannot reach OpenAI Responses API: {exc}") from exc
        if result.get("status") != "completed":
            raise RuntimeError(f"OpenAI response did not complete: {result.get('status')}")
        try:
            return json.loads(result["output_text"])
        except (KeyError, json.JSONDecodeError) as exc:
            raise RuntimeError("OpenAI response did not contain valid JSON") from exc

    def embed(self, text: str) -> list[float] | None:
        # Hold retrieval fixed against the Ollama baseline for the first
        # cross-provider comparison; this isolates consolidation and action choice.
        return self.retrieval.embed(text)

    def metadata(self) -> dict[str, str]:
        return {"provider": "openai-responses", "model": self.model, "embedding_model": self.retrieval.embedding_model}


def create_model_client() -> ModelClient:
    ollama = OllamaClient(
        os.getenv("OLLAMA_BASE_URL", "http://host.docker.internal:11434"),
        os.getenv("AGENT_MODEL", "qwen3.5:9b"),
        os.getenv("EMBEDDING_MODEL", "qwen3-embedding:0.6b"),
    )
    provider = os.getenv("MODEL_PROVIDER", "ollama")
    if provider == "ollama":
        return ollama
    if provider == "openai":
        return OpenAIResponsesClient(os.getenv("OPENAI_API_KEY", ""), os.getenv("OPENAI_MODEL", ""), ollama)
    raise RuntimeError(f"unknown MODEL_PROVIDER: {provider}")
