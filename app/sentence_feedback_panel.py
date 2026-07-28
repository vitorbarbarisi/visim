"""Bottom bar: student writes a Mandarin sentence, an LLM teacher corrects it."""
import tkinter as tk
from tkinter import ttk
from typing import Optional

from deepseek_client import (
    DeepSeekError,
    DeepSeekHttpError,
    DeepSeekResponseError,
    DeepSeekTimeoutError,
    MissingApiKeyError,
)
from scroll_utils import wheel_step


class SentenceFeedbackPanel:
    RESPONSE_LINES = 3  # compact: the bar must not eat the canvas
    MAX_INPUT_CHARS = 500
    PLACEHOLDER = ("Escreva uma frase em mandarim e clique em Enviar "
                   "(ou pressione Enter) para receber o feedback do professor.")

    def __init__(self, parent, deepseek_client, tasks):
        self.client = deepseek_client
        self.tasks = tasks

        self._request_seq = 0  # bumped per submit to discard stale async results
        self._pending = False  # a request is in flight

        self.frame = ttk.Frame(parent, relief="solid", borderwidth=1,
                               padding=(6, 4))
        self._build()

    def _build(self) -> None:
        self.frame.columnconfigure(0, weight=1)

        input_row = ttk.Frame(self.frame)
        input_row.grid(row=0, column=0, sticky=(tk.W, tk.E))
        input_row.columnconfigure(0, weight=1)

        self.input_var = tk.StringVar()
        self.entry = ttk.Entry(input_row, textvariable=self.input_var,
                               font=("Arial", 13))
        self.entry.grid(row=0, column=0, sticky=(tk.W, tk.E))
        self.entry.bind("<Return>", self._submit)
        self.entry.bind("<KP_Enter>", self._submit)

        self.send_button = ttk.Button(input_row, text="Enviar", width=10,
                                      command=self._submit)
        self.send_button.grid(row=0, column=1, padx=(6, 0))

        output_row = ttk.Frame(self.frame)
        output_row.grid(row=1, column=0, sticky=(tk.W, tk.E), pady=(4, 0))

        # height= in text lines is what bounds the bar: the parent grid row has
        # no weight and no N/S sticky, so nothing stretches it and long answers
        # scroll internally instead of growing the bar.
        self.response_text = tk.Text(output_row, wrap="word",
                                     height=self.RESPONSE_LINES,
                                     font=("Arial", 12), bg="white",
                                     fg="#212529", relief="solid",
                                     borderwidth=1, padx=15, pady=10,
                                     takefocus=False)
        scrollbar = ttk.Scrollbar(output_row, orient="vertical",
                                  command=self.response_text.yview)
        self.response_text.configure(yscrollcommand=scrollbar.set)
        self.response_text.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")

        for seq in ("<MouseWheel>", "<Button-4>", "<Button-5>"):
            self.response_text.bind(seq, self._on_mousewheel)
        self.response_text.bind("<Control-c>", self._on_copy_shortcut)
        self.response_text.bind("<Command-c>", self._on_copy_shortcut)

        self._configure_tags()
        self._render(self.PLACEHOLDER, "info")

    def _configure_tags(self) -> None:
        self.response_text.tag_configure("feedback", font=("Arial", 12),
                                         foreground="#212529")
        self.response_text.tag_configure("info", font=("Arial", 10),
                                         foreground="#6c757d")
        self.response_text.tag_configure("error", font=("Arial", 11, "bold"),
                                         foreground="#dc3545")

    # ------------------------------------------------------------------ #
    #  Submit + async lifecycle                                           #
    # ------------------------------------------------------------------ #

    def _submit(self, _event=None) -> Optional[str]:
        sentence = self.input_var.get().strip()
        if not sentence:
            self._render("Digite uma frase em mandarim antes de enviar.", "error")
            return "break"
        if len(sentence) > self.MAX_INPUT_CHARS:
            self._render(
                f"A frase é longa demais (máximo de {self.MAX_INPUT_CHARS} caracteres).",
                "error")
            return "break"
        if self._pending:
            return "break"  # a request is already in flight; first answer wins

        self._request_seq += 1
        token = self._request_seq
        self._pending = True
        self.send_button.state(["disabled"])
        self._render("Carregando…", "info")

        # on_error matters here: without it a network failure would leave the
        # bar stuck on "Carregando…" forever (TaskRunner drops None callbacks).
        self.tasks.submit(
            lambda: self.client.review_sentence(sentence),
            lambda feedback: self._on_feedback(token, feedback),
            lambda exc: self._on_failure(token, exc),
        )
        return "break"

    def _on_feedback(self, token: int, feedback: str) -> None:
        if token != self._request_seq:
            return  # a newer submit superseded this one
        self._finish()
        self._render(feedback, "feedback")

    def _on_failure(self, token: int, exc: Exception) -> None:
        if token != self._request_seq:
            return
        self._finish()
        print(f"Erro ao pedir feedback da frase: {exc!r}")
        self._render(self._describe_error(exc), "error")

    def _finish(self) -> None:
        self._pending = False
        try:
            self.send_button.state(["!disabled"])
        except tk.TclError:
            pass  # widget destroyed during shutdown

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

    # ------------------------------------------------------------------ #
    #  Response area                                                      #
    # ------------------------------------------------------------------ #

    def _render(self, message: str, tag: str) -> None:
        """The only writer to the response area. Keeps it read-only and, for
        long answers, anchored at the top rather than scrolled to the end."""
        try:
            self.response_text.config(state="normal")
            self.response_text.delete("1.0", "end")
            self.response_text.insert("end", message, tag)
            self.response_text.mark_set("insert", "1.0")
            self.response_text.see("1.0")
            self.response_text.config(state="disabled")
        except tk.TclError:
            pass  # widget destroyed during shutdown

    def _on_mousewheel(self, event) -> Optional[str]:
        step = wheel_step(event)
        if step is None:
            return None
        self.response_text.yview_scroll(step, "units")
        return "break"  # don't let the wheel also scroll the canvas underneath

    def _on_copy_shortcut(self, event) -> str:
        try:
            selection = self.response_text.get("sel.first", "sel.last")
        except tk.TclError:
            return "break"  # nothing selected
        if selection:
            self.frame.clipboard_clear()
            self.frame.clipboard_append(selection)
        return "break"
