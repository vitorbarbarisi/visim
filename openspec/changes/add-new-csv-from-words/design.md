## Context

O app já tem o menu **Arquivo** com "Abrir…" e "Reabrir recente", construído em `app/menu_builder.py`. CSVs vivem em `files/` na raiz do repo e são carregados/persistidos por `app/csv_repository.py` (`CsvWordRepository`). O orquestrador `WordCanvasApp` (em `app/word_canvas_app.py`) já expõe `_open_csv(path)` que cuida de tudo após o usuário escolher um arquivo: persiste em recentes, atualiza título, carrega palavras e redesenha o canvas.

Não existe hoje nenhuma forma de criar um novo CSV pelo app — o usuário precisa criar o arquivo manualmente.

## Goals / Non-Goals

**Goals:**
- Adicionar fluxo "Novo…" no menu **Arquivo** que abre um modal e cria um CSV em `files/`.
- Reaproveitar a infraestrutura existente: `CsvWordRepository` para escrita, `WordCanvasApp._open_csv` para o load subsequente.
- Manter o código alinhado aos princípios do `CLAUDE.md` (SOLID): o modal vira um módulo próprio com responsabilidade única; a lógica de transformar a lista de palavras em linhas de CSV também é isolada.

**Non-Goals:**
- Não vamos editar o `position_y` de forma adaptativa (sem cálculo baseado em `size` ou bbox); `DELTA=300` fixo.
- Não vamos buscar pinyin/translation no momento da criação — `has_pinyin/has_translation=true` apenas marcam a intenção; os valores ficam vazios e podem ser preenchidos depois pelo fluxo já existente de toggle (`P`/`T`).
- Não vamos suportar import de outros formatos (TSV, XLSX, etc.).
- Não vamos sobrescrever silenciosamente arquivos existentes — confirmar antes.

## Decisions

### 1. Novo módulo `app/new_file_dialog.py` com classe `NewFileDialog`
Encapsula um `tk.Toplevel` modal com: `Text` multilinhas para palavras, `Entry` para nome, botões "Criar" e "Cancelar". Expõe um único método público `ask() -> Optional[NewFileResult]` (síncrono, bloqueante via `wait_window`).

**Por quê:** SRP — UI do modal isolada, fácil de testar manualmente e de evoluir. Alinha com o estilo dos painéis (`word_info_panel.py`, `character_tabs_panel.py`).

**Alternativa considerada:** Embutir o modal dentro de `menu_builder.py`. Rejeitada porque infla o menu builder com responsabilidades de UI complexa e prejudica a leitura.

### 2. Parser de palavras com remoção de aspas
Função pura em `new_file_dialog.py` (ou módulo dedicado): aceita o texto bruto e devolve `List[str]` de palavras. Para cada linha: `strip()`, remover caracteres de aspas em qualquer posição (`"`, `'`, `“`, `”`, `‘`, `’`, `『`, `』`, `「`, `」`), depois `strip()` novamente; descartar linhas vazias e duplicatas consecutivas.

**Por quê:** O input do exemplo usa aspas retas mas usuários podem colar aspas tipográficas (comum em macOS). Remoção em qualquer posição é mais robusta que só nas pontas.

### 3. Geração do CSV via `CsvWordRepository.save`
Em vez de criar um writer paralelo, construir a `List[Dict]` no formato canônico que o repositório já entende:

```python
[{
  'word': w, 'size': 64,
  'position': {'x': 50, 'y': i * DELTA},
  'hasPinyin': True, 'hasTranslation': True,
  'pinyin': '', 'translation': '', 'tonePair': '',
} for i, w in enumerate(words)]
```

Depois chamar `CsvWordRepository(path).save(rows)`.

**Por quê:** Reaproveita o caminho de escrita já testado; uma única fonte de verdade para o formato.

**Alternativa considerada:** Função `write_new_csv(path, words)` separada. Rejeitada — gera duplicação do schema e abre brecha para divergência.

### 4. Constante `DELTA = 300` em `word_canvas_app.py` (ou no chamador)
Por ora, constante de módulo `NEW_FILE_Y_DELTA = 300` exportada por `word_canvas_app.py`. Documentada com `# a ser ajustada após testes`.

**Por quê:** Único ponto para ajustar quando o valor for revisado.

### 5. Nome de arquivo: validação mínima + auto-`.csv`
- Default: `datetime.date.today().strftime("%Y_%m_%d")`.
- Sanitização: remover separadores de caminho (`/`, `\`), `strip()` whitespace. Rejeitar nomes vazios.
- Se não termina em `.csv` (case-insensitive), acrescentar.
- Se o arquivo final já existe em `files/`: exibir `messagebox.askyesno` para confirmar sobrescrita.

**Por quê:** Sobrescrever silenciosamente é destrutivo; perguntar evita perda de trabalho.

### 6. Pasta de destino
Sempre `<repo_root>/files/`, criada se não existir (`os.makedirs(..., exist_ok=True)`). `repo_root` derivado de `os.path.dirname(os.path.dirname(__file__))` (mesma convenção que `MenuBuilder._open_dialog`).

### 7. Pós-criação
Após gravar, o callback no `WordCanvasApp` chama `self._open_csv(new_path)`, o que já cuida de:
- adicionar aos recentes,
- atualizar `last_csv_path`,
- atualizar título,
- recarregar e redesenhar.

**Por quê:** Reaproveitamento puro — zero duplicação.

## Risks / Trade-offs

- **[Risco] DELTA=300 pode ficar muito apertado ou muito esparso para tamanhos `size=64`.** → Mitigação: marcamos como "a ser ajustada" e o usuário pode mover/redimensionar livremente após a criação; constante em um único lugar facilita o ajuste.
- **[Risco] Usuário cola texto com palavras separadas por vírgula ou por espaços.** → Mitigação: documentar no placeholder do `Text` que cada palavra deve estar em sua própria linha. Não tentar "adivinhar" separadores no MVP.
- **[Risco] Nome do arquivo contém caracteres inválidos no sistema de arquivos.** → Mitigação: bloquear `/`, `\` e nomes vazios. Outros caracteres exóticos são responsabilidade do SO e tendem a funcionar no macOS/Linux.
- **[Risco] Modal trava UI se o usuário deixar aberto.** → Aceitável: é um modal por design (`grab_set` + `wait_window`).
- **[Trade-off] Não buscamos pinyin/translation na criação.** → Mantém o passo rápido e offline-friendly; o usuário pode habilitar por palavra via `P`/`T` depois.

## Open Questions

- Devemos pré-preencher o `pinyin`/`translation` chamando `word-api` para cada palavra no momento da criação? Decisão atual: **não** (escopo do MVP).
- O valor de `DELTA` deve ser configurável via UI? Decisão atual: **não** — constante de código, sob revisão.
