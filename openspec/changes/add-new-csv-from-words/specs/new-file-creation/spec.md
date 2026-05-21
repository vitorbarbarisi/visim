## ADDED Requirements

### Requirement: "Novo…" entry in the File menu
The application SHALL expose a **Novo…** menu item under the **Arquivo** menu, listed immediately above the existing **Abrir…** item.

#### Scenario: Menu entry is visible
- **WHEN** the user opens the **Arquivo** menu
- **THEN** an item labelled **Novo…** is shown above **Abrir…**

#### Scenario: Activating the menu entry opens the modal
- **WHEN** the user clicks **Arquivo → Novo…**
- **THEN** a modal dialog titled "Novo arquivo" opens
- **AND** the rest of the application is non-interactable until the modal is closed

### Requirement: New file modal layout
The "Novo arquivo" modal SHALL contain a multi-line text input for words, a single-line text input for the file name, and **Criar** / **Cancelar** buttons.

#### Scenario: Default file name is today's date
- **WHEN** the modal opens
- **THEN** the file name input is pre-filled with the current local date formatted as `aaaa_mm_dd` (e.g., `2026_05_20`)

#### Scenario: Cancel discards input
- **WHEN** the user clicks **Cancelar** (or closes the window) at any time
- **THEN** the modal closes without creating any file
- **AND** the current canvas/state is unchanged

### Requirement: Word list parsing
The system SHALL parse the multi-line input as one word per line, stripping surrounding whitespace and removing quote characters (`"`, `'`, `“`, `”`, `‘`, `’`, `「`, `」`, `『`, `』`) from each line.

#### Scenario: Quoted words are accepted
- **GIVEN** the input contains lines like `"著"` and `"當"`
- **WHEN** the user confirms creation
- **THEN** the parsed words are `著` and `當` (no quotes)

#### Scenario: Empty lines are ignored
- **GIVEN** the input contains blank lines between words
- **WHEN** the user confirms creation
- **THEN** the blank lines are skipped and only non-empty words are written to the CSV

#### Scenario: Empty input is rejected
- **WHEN** the user clicks **Criar** with no parsed words (empty or whitespace-only input)
- **THEN** an error message is shown explaining that at least one word is required
- **AND** the modal stays open

### Requirement: File name handling
The system SHALL sanitize and validate the file name, append `.csv` if missing, and place the new file inside the project's `files/` directory.

#### Scenario: `.csv` extension auto-appended
- **GIVEN** the file name input is `2026_05_20`
- **WHEN** the user clicks **Criar**
- **THEN** the resulting file is `files/2026_05_20.csv`

#### Scenario: Existing extension is preserved
- **GIVEN** the file name input is `my_words.csv`
- **WHEN** the user clicks **Criar**
- **THEN** the resulting file is `files/my_words.csv` (no double extension)

#### Scenario: Path separators are rejected
- **WHEN** the file name input contains `/` or `\`
- **THEN** **Criar** displays an error explaining that the name cannot contain path separators
- **AND** the modal stays open

#### Scenario: Empty file name is rejected
- **WHEN** the file name input is empty or whitespace-only at submission
- **THEN** **Criar** displays an error explaining that a file name is required
- **AND** the modal stays open

#### Scenario: Overwrite is confirmed
- **GIVEN** `files/<name>.csv` already exists
- **WHEN** the user clicks **Criar**
- **THEN** a confirmation dialog asks whether to overwrite
- **AND** the file is overwritten only if the user confirms

### Requirement: CSV row generation
The generated CSV SHALL use the existing canonical header `word,size,position_x,position_y,has_pinyin,has_translation,pinyin,translation,tone_pair` and produce one row per parsed word with the following column values: `size=64`, `position_x=50`, `position_y = index * DELTA` where `DELTA=300` and `index` starts at 0 in input order, `has_pinyin=true`, `has_translation=true`, and `pinyin`, `translation`, `tone_pair` empty.

#### Scenario: Row values match the spec
- **GIVEN** the parsed words are `[著, 當, 與]`
- **WHEN** the file is generated
- **THEN** the file contents are exactly:
  ```
  word,size,position_x,position_y,has_pinyin,has_translation,pinyin,translation,tone_pair
  著,64,50,0,true,true,,,
  當,64,50,300,true,true,,,
  與,64,50,600,true,true,,,
  ```

### Requirement: Load the new file after creation
After successfully creating the CSV, the application SHALL load it as the current file: redraw the canvas, add the path to the recent files list, persist it as the last opened CSV, and update the window title.

#### Scenario: New file becomes the active CSV
- **GIVEN** the user confirmed creation of `files/2026_05_20.csv` containing 10 words
- **WHEN** the modal closes
- **THEN** the canvas displays the 10 words at the positions written in the file
- **AND** the window title reflects the new file name
- **AND** `files/2026_05_20.csv` appears at the top of **Arquivo → Reabrir recente**
