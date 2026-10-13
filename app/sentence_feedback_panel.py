"""Bottom bar: student writes a Mandarin sentence, then either drops it on the
canvas whole (Enter / "Inserir") or asks an LLM teacher to correct it (✨ /
Cmd+Enter).

The bar is input only. Inserting goes through the injected on_insert callback,
so the bar never learns what a canvas is; every correction output — loading,
feedback, errors — goes to the injected view (see FeedbackWindow), so the main
window keeps a single slim row and the correction gets a whole window to be
readable in.
"""
import tkinter as tk
from tkinter import ttk
from typing import Callable, Optional

from deepseek_client import (
    DeepSeekError,
    DeepSeekHttpError,
    DeepSeekResponseError,
    DeepSeekTimeoutError,
    MissingApiKeyError,
)


class SentenceFeedbackPanel:
    MAX_INPUT_CHARS = 500
    INSERT_LABEL = "Inserir ↵"
    REVIEW_LABEL = "✨"

    def __init__(self, parent, deepseek_client, tasks, feedback_view,
                 on_insert: Callable[[str], None]):
        self.client = deepseek_client
        self.tasks = tasks
        self.view = feedback_view
        self.on_insert = on_insert

        self._request_seq = 0  # bumped per submit to discard stale async results
        self._pending = False  # a request is in flight

        self.frame = ttk.Frame(parent, relief="solid", borderwidth=1,
                               padding=(8, 6))
        self._build()

    def _build(self) -> None:
        self.frame.columnconfigure(0, weight=1)

        self.input_var = tk.StringVar()
        self.entry = ttk.Entry(self.frame, textvariable=self.input_var,
                               font=("Arial", 13))
        self.entry.grid(row=0, column=0, sticky=(tk.W, tk.E))
        self.entry.bind("<Return>", self._insert)
        self.entry.bind("<KP_Enter>", self._insert)
        self.entry.bind("<Command-Return>", self._submit)

        # The insert button is the wide one: it is the everyday action and the
        # one Enter triggers. The AI review is the occasional extra.
        self.insert_button = ttk.Button(self.frame, text=self.INSERT_LABEL,
                                        width=10, command=self._insert)
        self.insert_button.grid(row=0, column=1, padx=(8, 0))

        self.review_button = ttk.Button(self.frame, text=self.REVIEW_LABEL,
                                        width=3, command=self._submit)
        self.review_button.grid(row=0, column=2, padx=(4, 0))

    # ------------------------------------------------------------------ #
    #  Insert on canvas                                                   #
    # ------------------------------------------------------------------ #

    def _insert(self, _event=None) -> str:
        sentence = self.input_var.get().strip()
        if sentence:
            self.on_insert(sentence)
            self.input_var.set("")
        self._keep_typing()
        return "break"

    # ------------------------------------------------------------------ #
    #  Submit + async lifecycle                                           #
    # ------------------------------------------------------------------ #

    def _submit(self, _event=None) -> Optional[str]:
        sentence = self.input_var.get().strip()
        if not sentence:
            return self._reject("Digite uma frase em mandarim antes de enviar.")
        if len(sentence) > self.MAX_INPUT_CHARS:
            return self._reject(
                f"A frase é longa demais (máximo de {self.MAX_INPUT_CHARS} caracteres).")
        if self._pending:
            return "break"  # a request is already in flight; first answer wins

        self._request_seq += 1
        token = self._request_seq
        self._pending = True
        self.review_button.state(["disabled"])
        self.view.show_info("Carregando…")
        self._keep_typing()

        # on_error matters here: without it a network failure would leave the
        # window stuck on "Carregando…" forever (TaskRunner drops None callbacks).
        self.tasks.submit(
            lambda: self.client.review_sentence(sentence),
            lambda feedback: self._on_feedback(token, feedback),
            lambda exc: self._on_failure(token, exc),
        )
        return "break"

    def _reject(self, message: str) -> str:
        self.view.show_error(message)
        self._keep_typing()
        return "break"

    def _on_feedback(self, token: int, feedback: str) -> None:
        if token != self._request_seq:
            return  # a newer submit superseded this one
        self._finish()
        self.view.show_markdown(feedback)
        self._keep_typing()

    def _on_failure(self, token: int, exc: Exception) -> None:
        if token != self._request_seq:
            return
        self._finish()
        print(f"Erro ao pedir feedback da frase: {exc!r}")
        self.view.show_error(self._describe_error(exc))
        self._keep_typing()

    def _finish(self) -> None:
        self._pending = False
        try:
            self.review_button.state(["!disabled"])
        except tk.TclError:
            pass  # widget destroyed during shutdown

    def _keep_typing(self) -> None:
        """Return focus to the field: showing the pop-up must not interrupt
        someone mid-sentence."""
        try:
            self.entry.focus_set()
        except tk.TclError:
            pass

    def _describe_error(self, exc: Exception) -> str:
        if isinstance(exc, MissingApiKeyError):
            return ("Chave da API DeepSeek não configurada. Defina "
                    "DEEPSEEK_API_KEY no .env e reinicie o app.")
        if isinstance(exc, DeepSeekTimeoutError):
            return "A IA demorou demais para responder. Tente novamente."
        if isinstance(exc, DeepSeekHttpError):
            status = exc.status_code
            if status in (401, 403):
                return f"Chave da API DeepSeek recusada (erro {status})."
            if status == 402:
                return "Sem saldo na conta DeepSeek (erro 402)."
            if status == 429:
                return ("Limite de uso da API atingido (erro 429). "
                        "Aguarde e tente novamente.")
            return f"A IA respondeu com erro {status}. Tente novamente em instantes."
        if isinstance(exc, DeepSeekResponseError):
            return "Resposta inesperada da IA. Tente novamente."
        if isinstance(exc, DeepSeekError):
            return f"Não foi possível falar com a IA: {exc}"
        return f"Erro inesperado: {exc}"
