## Why

Hoje só é possível abrir CSVs já existentes em disco. Para começar a estudar um novo conjunto de palavras, o usuário precisa criar o arquivo CSV manualmente (com cabeçalho, posições, flags etc.), o que é trabalhoso e propenso a erro. Permitir a criação de um novo arquivo a partir de uma lista colada de palavras em mandarim torna o app utilizável como ponto de partida para uma sessão de estudo, sem editor externo.

## What Changes

- Adicionar item **"Novo…"** ao menu **Arquivo**, acima de "Abrir…".
- Abrir um modal com:
  - Campo de texto multilinhas: usuário cola/digita uma palavra por linha; aspas (`"`, `“`, `”`, `'`) em torno de cada palavra são ignoradas; linhas vazias são descartadas.
  - Campo de texto para o nome do arquivo, pré-preenchido com a data atual no formato `aaaa_mm_dd`.
  - Botões **Criar** e **Cancelar**.
- Ao confirmar, gerar um novo CSV em `files/<nome>.csv` (acrescentando `.csv` se ausente) com cabeçalho padrão e uma linha por palavra:
  - `size=64`, `position_x=50`, `position_y` começando em `0` e incrementando `DELTA=300` por linha,
  - `has_pinyin=true`, `has_translation=true`,
  - `pinyin`, `translation`, `tone_pair` vazios.
- Após a gravação: carregar o CSV recém-criado no canvas, atualizar a lista de "Reabrir recente" e o título da janela.

## Capabilities

### New Capabilities
- `new-file-creation`: criação de um novo arquivo CSV de palavras a partir de uma lista colada no modal "Novo…".

### Modified Capabilities
<!-- Nenhuma. Não há specs preexistentes em openspec/specs/. -->

## Impact

- **UI**: novo item de menu e novo modal (`app/new_file_dialog.py`, a criar) acionado por `menu_builder.py`.
- **Código**:
  - `app/menu_builder.py` — adicionar entrada "Novo…" e callback.
  - `app/word_canvas_app.py` — wire-up do callback que orquestra a criação do CSV e o carregamento subsequente.
  - `app/csv_repository.py` ou novo módulo `app/new_csv_builder.py` — geração das linhas a partir das palavras.
- **Filesystem**: novos arquivos serão escritos em `files/`. Nenhuma alteração no formato CSV existente.
- **Dependências**: nenhuma. Usa apenas `tkinter` e bibliotecas já presentes.
- **Configuração**: `DELTA=300` é constante por enquanto; documentar como "a ser testado".
