"""HTTP client for the DeepSeek chat-completions API.

DeepSeek is OpenAI-compatible, so plain `requests` is enough — no need for the
openai/langchain stack that the sibling hanzi-api repo uses. Mirrors the shape
of WordApiClient (class-constant defaults, constructor overrides).

Pure transport: no filesystem, no os.environ, no Tk. The API key is injected,
and it never appears in a log line, an exception message or a returned value.
"""
from typing import Optional, Tuple, Union

import requests

SENTENCE_REVIEW_SYSTEM_PROMPT = (
    "Você é um professor de chinês para brasileiros no nível básico. "
    "O aluno escreveu uma frase em mandarim tradicional. "
    "Dê um feedback sobre a frase, corrigindo erros, melhorando para usos em maior "
    "conformidade com a língua e dizendo se a frase está inteligível ou não para um chinês."
)


class DeepSeekError(Exception):
    """Base class for every DeepSeek failure surfaced to the UI."""


class MissingApiKeyError(DeepSeekError):
    pass


class DeepSeekTimeoutError(DeepSeekError):
    pass


class DeepSeekHttpError(DeepSeekError):
    """Non-200 response. Carries the response body only — never the headers,
    which hold the Authorization bearer token."""

    def __init__(self, status_code: int, body: str = ""):
        super().__init__(f"HTTP {status_code}: {body}")
        self.status_code = status_code
        self.body = body


class DeepSeekResponseError(DeepSeekError):
    """200 but the payload wasn't the expected chat-completion shape."""


class DeepSeekClient:
    DEFAULT_BASE_URL = "https://api.deepseek.com/v1"
    DEFAULT_MODEL = "deepseek-chat"
    # (connect, read). The read budget matches hanzi-api's request_timeout=60;
    # WordApiClient's 5s is far too short for an LLM round-trip.
    DEFAULT_TIMEOUT: Tuple[float, float] = (5, 60)

    def __init__(self, api_key: Optional[str] = None,
                 base_url: Optional[str] = None,
                 model: Optional[str] = None,
                 timeout: Union[float, Tuple[float, float], None] = None,
                 verify: Union[bool, str] = True):
        # A missing key must NOT raise here: the app builds this client
        # unconditionally at startup and only surfaces the problem on submit.
        self.api_key = (api_key or "").strip() or None
        self.base_url = (base_url or self.DEFAULT_BASE_URL).rstrip("/")
        self.model = model or self.DEFAULT_MODEL
        self.timeout = timeout or self.DEFAULT_TIMEOUT
        # True, False, or a CA-bundle path — see env_loader.read_ssl_verify.
        self.verify = verify
        if verify is False:
            # Say it once, loudly, instead of letting urllib3 spam a warning
            # per request. Verification off means a MITM proxy can read the
            # request, which includes the bearer token.
            print("DeepSeek: verificação de certificado TLS DESATIVADA "
                  "(SSL_VERIFY=false)")
            try:
                import urllib3
                urllib3.disable_warnings(
                    urllib3.exceptions.InsecureRequestWarning)
            except Exception:
                pass

    @property
    def configured(self) -> bool:
        return self.api_key is not None

    def review_sentence(self, sentence: str) -> str:
        """Ask the teacher persona to correct a Mandarin sentence. Blocking —
        call it off the Tk main thread (see TaskRunner)."""
        return self._chat(SENTENCE_REVIEW_SYSTEM_PROMPT, f"Frase do aluno: {sentence}")

    def _chat(self, system_prompt: str, user_prompt: str) -> str:
        if not self.api_key:
            raise MissingApiKeyError("DEEPSEEK_API_KEY não configurada")

        url = f"{self.base_url}/chat/completions"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": 0,
            "stream": False,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        print(f"DeepSeek: POST {url} (model={self.model})")
        try:
            response = requests.post(url, json=payload, headers=headers,
                                     timeout=self.timeout, verify=self.verify)
        except requests.exceptions.Timeout as e:
            raise DeepSeekTimeoutError(str(e)) from e
        except requests.exceptions.RequestException as e:
            raise DeepSeekError(str(e)) from e

        if response.status_code != 200:
            raise DeepSeekHttpError(response.status_code, response.text[:200])

        try:
            content = response.json()["choices"][0]["message"]["content"]
        except (ValueError, KeyError, IndexError, TypeError) as e:
            raise DeepSeekResponseError(
                f"corpo inesperado: {response.text[:200]}") from e

        content = (content or "").strip()
        if not content:
            raise DeepSeekResponseError("resposta vazia")
        return content
