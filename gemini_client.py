"""Gemini REST API client for GlowMate.

Pure standard-library implementation using urllib.request and json.
Supports header authentication, model verification, structured output,
bounded retries with exponential backoff, credential sanitization,
usage tracking, and local response caching.
"""

from __future__ import annotations

import hashlib
import json
import random
import time
import urllib.error
import urllib.request
from typing import Any, Dict, Optional, Tuple

from config import GlowMateConfig


class GeminiAPIError(Exception):
    """Custom exception for Gemini API failures without credential leakage."""

    def __init__(self, message: str, status_code: Optional[int] = None, is_retryable: bool = False):
        super().__init__(message)
        self.status_code = status_code
        self.is_retryable = is_retryable


class GeminiClient:
    """Standard-library REST client for Google AI Studio Gemini API."""

    def __init__(self, config: GlowMateConfig):
        self.config = config
        self._stats_path = config.usage_stats_path
        self._cache_path = config.cache_path
        self._load_cache()

    # -------------------------------------------------------------------------
    # Sanitization & Security
    # -------------------------------------------------------------------------

    def sanitize_message(self, text: str) -> str:
        """Strip raw API key if it ever appears in text or error messages."""
        if self.config.api_key and self.config.api_key in text:
            return text.replace(self.config.api_key, "[REDACTED_API_KEY]")
        return text

    # -------------------------------------------------------------------------
    # Model Availability Verification
    # -------------------------------------------------------------------------

    def verify_model_availability(self) -> Tuple[bool, str]:
        """Check whether the configured model is available in the API.
        
        Returns (is_available, message).
        """
        if not self.config.has_api_key:
            return False, "GEMINI_API_KEY environment variable is not configured or is a placeholder."

        model_name = self.config.model.strip()
        # Models can be queried as models/{model}
        if not model_name.startswith("models/"):
            endpoint = f"{self.config.api_base_url}/models/{model_name}"
        else:
            endpoint = f"{self.config.api_base_url}/{model_name}"

        req = urllib.request.Request(
            endpoint,
            headers={
                "x-goog-api-key": self.config.api_key,
                "Content-Type": "application/json",
            },
            method="GET",
        )

        try:
            with urllib.request.urlopen(req, timeout=self.config.request_timeout_seconds) as response:
                if response.status == 200:
                    payload = json.loads(response.read().decode("utf-8"))
                    display_name = payload.get("displayName", model_name)
                    return True, f"Model '{model_name}' ({display_name}) is verified and available."
                return False, f"Unexpected status code {response.status} when verifying model '{model_name}'."
        except urllib.error.HTTPError as err:
            err_body = self._read_error_body(err)
            if err.code == 404:
                return False, f"Model '{model_name}' not found. Please verify GEMINI_MODEL."
            elif err.code == 400 and "API_KEY_INVALID" in err_body:
                return False, "API key is invalid. Please check your GEMINI_API_KEY."
            elif err.code == 403:
                return False, "API key does not have permission to access the Gemini API (HTTP 403)."
            return False, f"HTTP Error {err.code} while verifying model: {self.sanitize_message(err_body)}"
        except Exception as ex:
            return False, f"Network or connection error while verifying model: {self.sanitize_message(str(ex))}"

    # -------------------------------------------------------------------------
    # Cache Management
    # -------------------------------------------------------------------------

    def _load_cache(self) -> None:
        self.cache: Dict[str, Dict[str, Any]] = {}
        if self._cache_path.exists():
            try:
                with open(self._cache_path, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}

    def _save_cache(self) -> None:
        try:
            self._cache_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._cache_path, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2)
        except Exception:
            pass

    def compute_cache_key(self, prompt: str, profile_hash: str) -> str:
        """Create a stable hash key combining query, profile context, and model."""
        content = f"{self.config.model}:{profile_hash}:{prompt.strip().lower()}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    def get_cached_response(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Retrieve unexpired cached response if present."""
        if cache_key not in self.cache:
            return None
        entry = self.cache[cache_key]
        created_at = entry.get("timestamp", 0)
        ttl_seconds = self.config.cache_ttl_hours * 3600
        if time.time() - created_at > ttl_seconds:
            # Expired
            del self.cache[cache_key]
            self._save_cache()
            return None
        return entry.get("response")

    def store_cached_response(self, cache_key: str, response: Dict[str, Any]) -> None:
        """Store response in local cache with current timestamp."""
        self.cache[cache_key] = {
            "timestamp": time.time(),
            "response": response,
        }
        self._save_cache()

    def clear_cache(self) -> int:
        """Purge all entries from the local response cache."""
        count = len(self.cache)
        self.cache.clear()
        self._save_cache()
        return count

    # -------------------------------------------------------------------------
    # Usage Tracking
    # -------------------------------------------------------------------------

    def _update_usage(self, success: bool, prompt_tokens: int = 0, candidate_tokens: int = 0) -> None:
        stats = {
            "successful_requests": 0,
            "failed_requests": 0,
            "total_prompt_tokens": 0,
            "total_candidate_tokens": 0,
            "total_tokens": 0,
        }
        if self._stats_path.exists():
            try:
                with open(self._stats_path, "r", encoding="utf-8") as f:
                    stats.update(json.load(f))
            except Exception:
                pass

        if success:
            stats["successful_requests"] += 1
            stats["total_prompt_tokens"] += prompt_tokens
            stats["total_candidate_tokens"] += candidate_tokens
            stats["total_tokens"] += (prompt_tokens + candidate_tokens)
        else:
            stats["failed_requests"] += 1

        try:
            self._stats_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self._stats_path, "w", encoding="utf-8") as f:
                json.dump(stats, f, indent=2)
        except Exception:
            pass

    def get_usage_statistics(self) -> Dict[str, Any]:
        """Return total API call counts and token usage."""
        if self._stats_path.exists():
            try:
                with open(self._stats_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {
            "successful_requests": 0,
            "failed_requests": 0,
            "total_prompt_tokens": 0,
            "total_candidate_tokens": 0,
            "total_tokens": 0,
            "cache_entries": len(self.cache),
        }

    # -------------------------------------------------------------------------
    # Content Generation & Structured JSON Output
    # -------------------------------------------------------------------------

    def generate_structured_json(
        self,
        prompt: str,
        system_instruction: Optional[str] = None,
        profile_hash: str = "default",
        use_cache: bool = True,
    ) -> Dict[str, Any]:
        """Call Gemini REST API requesting structured JSON output.
        
        Uses responseMimeType='application/json' and bounded retries.
        """
        if not self.config.has_api_key:
            raise GeminiAPIError("GEMINI_API_KEY environment variable is not set or is empty.")

        cache_key = self.compute_cache_key(prompt, profile_hash)
        if use_cache:
            cached = self.get_cached_response(cache_key)
            if cached is not None:
                return cached

        # Prepare payload
        payload: Dict[str, Any] = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": prompt}],
                }
            ],
            "generationConfig": {
                "temperature": 0.3,
                "responseMimeType": "application/json",
            },
        }

        if system_instruction:
            payload["systemInstruction"] = {
                "parts": [{"text": system_instruction}]
            }

        model_name = self.config.model.strip()
        endpoint = f"{self.config.api_base_url}/models/{model_name}:generateContent"

        json_bytes = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            endpoint,
            data=json_bytes,
            headers={
                "x-goog-api-key": self.config.api_key,
                "Content-Type": "application/json",
            },
            method="POST",
        )

        response_data, usage_metadata = self._execute_request_with_retries(req)

        # Parse Gemini candidates
        try:
            candidates = response_data.get("candidates", [])
            if not candidates:
                feedback = response_data.get("promptFeedback", {})
                raise GeminiAPIError(f"No response candidate returned by Gemini. Feedback: {feedback}")

            content_parts = candidates[0].get("content", {}).get("parts", [])
            if not content_parts or "text" not in content_parts[0]:
                raise GeminiAPIError("Candidate did not contain text content.")

            raw_text = content_parts[0]["text"].strip()
            # Clean markdown code block wraps if model enclosed in ```json ... ```
            if raw_text.startswith("```"):
                lines = raw_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                raw_text = "\n".join(lines).strip()

            parsed_json = json.loads(raw_text)
            if not isinstance(parsed_json, dict):
                raise GeminiAPIError("Expected top-level JSON object from Gemini response.")

        except json.JSONDecodeError as jde:
            self._update_usage(success=False)
            raise GeminiAPIError(f"Model returned invalid JSON: {jde}") from jde

        # Record successful usage
        p_tok = usage_metadata.get("promptTokenCount", 0)
        c_tok = usage_metadata.get("candidatesTokenCount", 0)
        self._update_usage(success=True, prompt_tokens=p_tok, candidate_tokens=c_tok)

        # Cache valid response
        if use_cache:
            self.store_cached_response(cache_key, parsed_json)

        return parsed_json

    def _execute_request_with_retries(self, req: urllib.request.Request) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """Execute HTTP request with exponential backoff for transient errors."""
        last_exception: Optional[Exception] = None

        for attempt in range(self.config.max_retries + 1):
            try:
                with urllib.request.urlopen(req, timeout=self.config.request_timeout_seconds) as resp:
                    resp_bytes = resp.read()
                    data = json.loads(resp_bytes.decode("utf-8"))
                    usage = data.get("usageMetadata", {})
                    return data, usage

            except urllib.error.HTTPError as err:
                err_body = self._read_error_body(err)
                sanitized_body = self.sanitize_message(err_body)

                # Permanent client errors: 400, 401, 403, 404 (do NOT retry)
                if err.code in (400, 401, 403, 404):
                    self._update_usage(success=False)
                    raise GeminiAPIError(
                        f"HTTP {err.code} Permanent Error: {sanitized_body}",
                        status_code=err.code,
                        is_retryable=False,
                    )

                # Transient errors: 429 (rate limit / quota), 500, 503, 504
                is_retryable = err.code in (429, 500, 503, 504)
                last_exception = GeminiAPIError(
                    f"HTTP {err.code} Server/RateLimit Error: {sanitized_body}",
                    status_code=err.code,
                    is_retryable=is_retryable,
                )

                if attempt >= self.config.max_retries or not is_retryable:
                    self._update_usage(success=False)
                    raise last_exception

                # Exponential backoff with jitter
                sleep_time = (self.config.retry_backoff_factor ** attempt) + random.uniform(0.1, 0.5)
                time.sleep(sleep_time)

            except (urllib.error.URLError, TimeoutError) as net_err:
                sanitized_msg = self.sanitize_message(str(net_err))
                last_exception = GeminiAPIError(
                    f"Network or timeout error: {sanitized_msg}",
                    status_code=None,
                    is_retryable=True,
                )
                if attempt >= self.config.max_retries:
                    self._update_usage(success=False)
                    raise last_exception

                sleep_time = (self.config.retry_backoff_factor ** attempt) + random.uniform(0.1, 0.5)
                time.sleep(sleep_time)

        self._update_usage(success=False)
        raise last_exception or GeminiAPIError("Maximum retries exceeded.")

    def _read_error_body(self, err: urllib.error.HTTPError) -> str:
        try:
            return err.read().decode("utf-8")
        except Exception:
            return str(err)
