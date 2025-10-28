#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Word Canvas Application
Aplicação gráfica para carregar palavras do CSV e permitir drag and drop
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from tkinter import font as tkfont
import csv
import os
import json
from typing import List, Dict, Tuple, Optional
from gtts import gTTS
import pygame
import tempfile
import threading
import time
import tkinterweb
import webbrowser
import webview
import subprocess
import sys
import requests
import urllib.parse

class WordCanvasApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Word Canvas")
        self.root.geometry("1200x600")  # Increased width for side panel
        
        # Track current CSV path (default to files/words.csv at project root)
        self.current_csv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), "files", "words.csv")
        # Try to use last opened CSV from user config
        self.load_last_csv_path()
        # Recent files list
        self.recent_csv_paths: List[str] = []
        self.load_recent_csv_paths()
        self.update_window_title_with_csv()
        
        # Data storage
        self.words_data: List[Dict] = []
        self.word_objects: List[Dict] = {}
        self.selected_word_id: Optional[int] = None
        self.drag_data = {"x": 0, "y": 0, "item": None}
        
        # Audio system
        self.audio_cache = {}  # Cache for generated audio files
        self.audio_loading = False  # Flag to prevent multiple audio requests
        self.audio_available = False
        
        # Word info panel state (left side)
        self.word_panel_visible = False
        self.word_frame = None
        self.word_info_widgets = {}  # Dictionary to store word info panel widgets
        
        # Web panel state (right side)
        self.web_panel_visible = False
        self.web_frame = None
        self.web_notebook = None
        self.active_tabs = {}  # Dictionary to track active tabs by word
        self.opened_windows = {}  # Track opened webview windows
        
        # Initialize pygame mixer for audio playback
        try:
            pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)
            self.audio_available = True
            print("Audio system initialized successfully")
        except (pygame.error, NotImplementedError) as e:
            print(f"Audio system not available: {e}")
            print("Audio playback will use system default player")
        
        # Create UI
        self.create_widgets()
        self.load_words_from_csv()
        self.draw_words()
        
    def create_widgets(self):
        """Create the main UI components"""
        # Configure root window grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        
        # Menubar (Arquivo -> Abrir CSV…)
        self.create_menu()
        
        # Main PanedWindow for resizable layout
        self.main_paned = ttk.PanedWindow(self.root, orient=tk.HORIZONTAL)
        self.main_paned.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # Store initial sash positions for restoring when panels are reopened
        self.last_left_sash_position = None
        self.last_right_sash_position = None
        
        # Left side: Word info panel frame (initially hidden)
        self.word_frame = ttk.Frame(self.main_paned, relief="solid", borderwidth=1)
        # Don't add to paned window initially - will be shown when a word is clicked
        
        # Create the word info panel within the frame
        self.create_word_panel()
        
        # Center: Canvas with scrollbars
        canvas_frame = ttk.Frame(self.main_paned)
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)
        
        # Canvas with light gray background and scrollable area
        self.canvas = tk.Canvas(canvas_frame, bg="#f0f0f0", 
                               scrollregion=(0, 0, 2000, 2000))  # Large scrollable area
        self.canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbars for canvas
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.canvas.configure(yscrollcommand=v_scrollbar.set)
        
        h_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        h_scrollbar.grid(row=1, column=0, sticky=(tk.W, tk.E))
        self.canvas.configure(xscrollcommand=h_scrollbar.set)
        
        # Add canvas frame to center pane
        self.main_paned.add(canvas_frame, weight=2)
        # Note: minsize will be set after widget is fully initialized
        
        # Right side: Web panel frame (initially hidden)
        self.web_frame = ttk.Frame(self.main_paned, relief="solid", borderwidth=1)
        # Don't add to paned window initially - will be shown when a word is clicked
        
        # Create the web viewer within the frame
        self.create_web_panel()
        
        # Enable mouse wheel scrolling
        self.canvas.bind("<MouseWheel>", self._on_mousewheel)
        self.canvas.bind("<Button-4>", self._on_mousewheel)
        self.canvas.bind("<Button-5>", self._on_mousewheel)
        
        # Bind events
        self.canvas.bind("<Button-1>", self.on_canvas_click)
        self.canvas.bind("<B1-Motion>", self.on_canvas_drag)
        self.canvas.bind("<ButtonRelease-1>", self.on_canvas_release)
        
        # Bind keyboard events
        self.root.bind("<KeyPress>", self.on_key_press)
        self.root.focus_set()  # Enable keyboard focus
        
        # Bind window resize event
        self.root.bind("<Configure>", self.on_window_resize)
    
    def create_menu(self):
        """Create application menubar with 'Arquivo' menu"""
        self.menubar = tk.Menu(self.root)
        self.file_menu = tk.Menu(self.menubar, tearoff=0)
        self.file_menu.add_command(label="Abrir…", command=self.open_csv_file)
        # Recent files submenu
        self.recent_menu = tk.Menu(self.file_menu, tearoff=0)
        self.file_menu.add_cascade(label="Reabrir recente", menu=self.recent_menu)
        self.populate_recent_menu()
        self.file_menu.add_separator()
        self.file_menu.add_command(label="Sair", command=self.root.quit)
        self.menubar.add_cascade(label="Arquivo", menu=self.file_menu)
        self.root.config(menu=self.menubar)

    def update_window_title_with_csv(self):
        """Update window title with the current CSV file name"""
        try:
            base = os.path.basename(self.current_csv_path) if self.current_csv_path else ""
            self.root.title(f"Word Canvas - Drag & Drop — {base}")
        except Exception:
            # Fallback without file name
            self.root.title("Word Canvas - Drag & Drop")

    def get_user_config_path(self) -> str:
        """Return path to user config file (~/.visim/config.json)"""
        home_dir = os.path.expanduser("~")
        config_dir = os.path.join(home_dir, ".visim")
        return os.path.join(config_dir, "config.json")

    def load_last_csv_path(self):
        """Load last used CSV path from user config, if valid."""
        try:
            config_path = self.get_user_config_path()
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                last_path = data.get("last_csv_path")
                if last_path and isinstance(last_path, str) and os.path.isfile(last_path):
                    self.current_csv_path = os.path.abspath(last_path)
        except Exception:
            # Ignore config errors silently
            pass

    def save_last_csv_path(self):
        """Persist current CSV path to user config."""
        try:
            config_path = self.get_user_config_path()
            config_dir = os.path.dirname(config_path)
            os.makedirs(config_dir, exist_ok=True)
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump({"last_csv_path": self.current_csv_path}, f, ensure_ascii=False, indent=2)
        except Exception:
            # Ignore persistence errors silently
            pass

    def load_recent_csv_paths(self):
        """Load recent CSV paths from config and sanitize"""
        try:
            config_path = self.get_user_config_path()
            if os.path.exists(config_path):
                with open(config_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                recent = data.get("recent_csv_paths", [])
                if isinstance(recent, list):
                    seen = set()
                    cleaned = []
                    for p in recent:
                        if isinstance(p, str) and os.path.isfile(p) and p not in seen:
                            seen.add(p)
                            cleaned.append(p)
                    self.recent_csv_paths = cleaned[:10]
        except Exception:
            self.recent_csv_paths = []

    def save_recent_csv_paths(self):
        """Persist recent CSV paths to config, merging with other keys"""
        try:
            config_path = self.get_user_config_path()
            config_dir = os.path.dirname(config_path)
            os.makedirs(config_dir, exist_ok=True)
            payload = {}
            if os.path.exists(config_path):
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        payload = json.load(f) or {}
                except Exception:
                    payload = {}
            payload["recent_csv_paths"] = self.recent_csv_paths
            if "last_csv_path" not in payload:
                payload["last_csv_path"] = self.current_csv_path
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(payload, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def add_to_recent_files(self, path: str):
        """Add a path to recent list and persist"""
        try:
            abs_path = os.path.abspath(path) if path else None
            if not abs_path or not os.path.isfile(abs_path):
                return
            self.recent_csv_paths = [p for p in self.recent_csv_paths if p != abs_path]
            self.recent_csv_paths.insert(0, abs_path)
            self.recent_csv_paths = self.recent_csv_paths[:10]
            self.save_recent_csv_paths()
            self.populate_recent_menu()
        except Exception:
            pass

    def populate_recent_menu(self):
        """Rebuild the recent files submenu"""
        try:
            self.recent_menu.delete(0, "end")
        except Exception:
            return
        if not self.recent_csv_paths:
            self.recent_menu.add_command(label="Vazio", state="disabled")
        else:
            for p in self.recent_csv_paths:
                label = os.path.basename(p)
                self.recent_menu.add_command(label=label, command=lambda p=p: self.reopen_recent(p))
        self.recent_menu.add_separator()
        self.recent_menu.add_command(label="Limpar lista", command=self.clear_recent_files)

    def reopen_recent(self, path: str):
        """Open a recent CSV path if valid"""
        if not path or not os.path.isfile(path):
            self.recent_csv_paths = [p for p in self.recent_csv_paths if p != path]
            self.save_recent_csv_paths()
            self.populate_recent_menu()
            messagebox.showwarning("Arquivo não encontrado", "O arquivo recente não está mais disponível.")
            return
        self.current_csv_path = os.path.abspath(path)
        print(f"Abrindo CSV recente: {self.current_csv_path}")
        self.save_last_csv_path()
        self.update_window_title_with_csv()
        self.load_words_from_csv(self.current_csv_path)
        self.draw_words()

    def clear_recent_files(self):
        """Clear recent files list"""
        self.recent_csv_paths = []
        self.save_recent_csv_paths()
        self.populate_recent_menu()

    def open_csv_file(self):
        """Open a CSV file chosen by the user and reload the canvas"""
        filetypes = [("CSV", "*.csv"), ("Todos os arquivos", "*.*")]
        files_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), "files")
        initial_dir = files_dir if os.path.isdir(files_dir) else (os.path.dirname(self.current_csv_path) if self.current_csv_path else os.path.dirname(__file__))
        path = filedialog.askopenfilename(title="Abrir CSV", initialdir=initial_dir, filetypes=filetypes)
        if not path:
            return
        self.current_csv_path = os.path.abspath(path)
        print(f"Abrindo CSV: {self.current_csv_path}")
        self.add_to_recent_files(path)
        self.save_last_csv_path()
        self.update_window_title_with_csv()
        self.load_words_from_csv(self.current_csv_path)
        self.draw_words()

    def create_word_panel(self):
        """Create the word info panel with word details and related words list"""
        if self.word_frame:
            # Header with close button
            header_frame = ttk.Frame(self.word_frame)
            header_frame.pack(fill="x", padx=5, pady=5)
            
            # Title label
            self.word_title_label = ttk.Label(header_frame, text="Informações da Palavra", 
                                            font=("Arial", 12, "bold"))
            self.word_title_label.pack(side="left")
            
            # Close button
            close_button = ttk.Button(header_frame, text="×", width=3, 
                                    command=self.hide_word_panel)
            close_button.pack(side="right")
            
            # Main content frame
            content_frame = ttk.Frame(self.word_frame)
            content_frame.pack(fill="both", expand=True, padx=5, pady=(0, 5))
            
            # Word info section
            info_frame = ttk.LabelFrame(content_frame, text="Detalhes", padding=10)
            info_frame.pack(fill="x", pady=(0, 10))
            
            # Word info labels
            self.word_info_labels = {}
            info_items = [
                ("word", "Palavra:"),
                ("calls", "Calls:"),
                ("confidence", "Confidence Level:"),
                ("translations", "Traduções:")
            ]
            
            for key, label_text in info_items:
                label_frame = ttk.Frame(info_frame)
                label_frame.pack(fill="x", pady=2)
                
                label = ttk.Label(label_frame, text=label_text, font=("Arial", 10, "bold"))
                label.pack(side="left")
                
                value_label = ttk.Label(label_frame, text="", font=("Arial", 10))
                value_label.pack(side="left", padx=(10, 0))
                
                self.word_info_labels[key] = value_label
            
            # Related words section with notebook for tabs per character
            related_frame = ttk.LabelFrame(content_frame, text="Palavras Relacionadas", padding=10)
            related_frame.pack(fill="both", expand=True)
            
            # Notebook for character tabs
            self.related_words_notebook = ttk.Notebook(related_frame)
            self.related_words_notebook.pack(fill="both", expand=True)
            
            # Dictionary to store listboxes for each character
            self.related_words_listboxes = {}
            
            # Add initial placeholder content
            self.add_placeholder_word_info()
    
    def add_placeholder_word_info(self):
        """Add placeholder content when no word is selected"""
        # Clear existing content
        for label in self.word_info_labels.values():
            label.config(text="")
        
        # Clear related words notebook tabs
        if self.related_words_notebook:
            for tab_id in self.related_words_notebook.tabs():
                self.related_words_notebook.forget(tab_id)
        
        # Create placeholder tab
        placeholder_tab = ttk.Frame(self.related_words_notebook)
        self.related_words_notebook.add(placeholder_tab, text="Selecione")
        
        placeholder_label = ttk.Label(placeholder_tab, text="Clique em uma palavra para ver palavras relacionadas")
        placeholder_label.pack(pady=20)
        
        # Add placeholder text
        self.word_info_labels["word"].config(text="Selecione uma palavra")
        self.word_info_labels["calls"].config(text="")
        self.word_info_labels["confidence"].config(text="")
        self.word_info_labels["translations"].config(text="")
    
    def show_word_panel(self, word_data):
        """Show the word info panel with word details and related words"""
        if not self.word_panel_visible:
            # Add word frame to left pane of PanedWindow
            self.main_paned.insert(0, self.word_frame, weight=1)
            self.word_panel_visible = True
            
            # Set initial position to give reasonable split
            self.root.after_idle(self._set_initial_left_sash_position)
        
        # Update the title
        if hasattr(self, 'word_title_label'):
            self.word_title_label.config(text=f"Informações: {word_data['word']}")
        
        # Fetch word information from API
        word = word_data['word']
        word_info = self.fetch_word_info(word)
        
        # Update word info labels
        if word_info:
            self.word_info_labels["word"].config(text=word_info.get('word', word))
            self.word_info_labels["calls"].config(text=str(word_info.get('calls', 'N/A')))
            self.word_info_labels["confidence"].config(text=str(word_info.get('confidence_level', 'N/A')))
            
            # Format translations
            translations = word_info.get('translation', '')
            if isinstance(translations, list):
                translations = '; '.join(translations)
            self.word_info_labels["translations"].config(text=f'"{translations}"' if translations else 'N/A')
        else:
            # Fallback to local data
            self.word_info_labels["word"].config(text=word)
            self.word_info_labels["calls"].config(text="N/A")
            self.word_info_labels["confidence"].config(text="N/A")
            self.word_info_labels["translations"].config(text=f'"{word_data.get("translation", "N/A")}"')
        
        # Fetch related words - create tab for each character
        # Clear existing tabs
        if self.related_words_notebook:
            for tab_id in self.related_words_notebook.tabs():
                self.related_words_notebook.forget(tab_id)
        self.related_words_listboxes.clear()
        
        # Split word into individual characters
        characters = list(word)
        
        # Create tab for each Chinese character
        for char in characters:
            if self._is_chinese_char(char):
                # Create tab for this character
                char_tab = ttk.Frame(self.related_words_notebook)
                self.related_words_notebook.add(char_tab, text=char)
                
                # Create scrollable list for this character's related words
                list_frame = ttk.Frame(char_tab)
                list_frame.pack(fill="both", expand=True, padx=5, pady=5)
                
                # Scrollbar for the list
                scrollbar = ttk.Scrollbar(list_frame)
                scrollbar.pack(side="right", fill="y")
                
                # Listbox for related words
                listbox = tk.Listbox(list_frame, yscrollcommand=scrollbar.set,
                                    font=("Arial", 10), height=10)
                listbox.pack(side="left", fill="both", expand=True)
                scrollbar.config(command=listbox.yview)
                
                # Bind double-click to add word to canvas
                listbox.bind("<Double-Button-1>", self.on_related_word_double_click)
                
                # Store listbox reference
                self.related_words_listboxes[char] = listbox
                
                # Fetch related words for this character
                char_results = self.search_related_words(char)
                
                # Populate list
                if char_results:
                    # Sort by calls (descending)
                    char_results.sort(key=lambda x: x.get('calls', 0), reverse=True)
                    
                    for word_item in char_results:
                        # Format: word | pinyin | translation | calls | confidence
                        word_text = word_item.get('word', '')
                        pinyin = word_item.get('pinyin', '')
                        translation = word_item.get('translation', '')
                        calls = word_item.get('calls', '')
                        confidence = word_item.get('confidence_level', '')
                        display_text = f"{word_text} | {pinyin} | {translation} | {calls} | {confidence}"
                        listbox.insert(tk.END, display_text)
                else:
                    listbox.insert(tk.END, "Nenhuma palavra relacionada encontrada")
    
    def hide_word_panel(self):
        """Hide the word info panel"""
        if self.word_panel_visible:
            # Save current sash position before hiding
            try:
                self.last_left_sash_position = self.main_paned.sashpos(0)
            except tk.TclError:
                # No sash position available
                pass
            
            # Remove word frame from PanedWindow
            self.main_paned.remove(self.word_frame)
            self.word_panel_visible = False
    
    def _set_initial_left_sash_position(self):
        """Set initial left sash position to give reasonable split"""
        try:
            window_width = self.root.winfo_width()
            if window_width > 100:  # Make sure window is properly sized
                # Position at about 20% of window width for left panel
                sash_pos = int(window_width * 0.2)
                self.main_paned.sashpos(0, sash_pos)
        except (tk.TclError, AttributeError):
            # Fallback if there's any issue
            pass
    
    def on_related_word_double_click(self, event):
        """Handle double-click on related word to add it to canvas"""
        # Get the widget that was clicked
        widget = event.widget
        selection = widget.curselection()
        if selection:
            selected_text = widget.get(selection[0])
            # Extract word from display text (first part before |)
            word = selected_text.split(' | ')[0].strip()
            if word:
                self.add_word_to_canvas(word)
    
    def create_web_panel(self):
        """Create the web viewer panel with tabs for individual characters"""
        if self.web_frame:
            # Header with close button
            header_frame = ttk.Frame(self.web_frame)
            header_frame.pack(fill="x", padx=5, pady=5)
            
            # Title label
            self.web_title_label = ttk.Label(header_frame, text="Caracteres", 
                                           font=("Arial", 12, "bold"))
            self.web_title_label.pack(side="left")
            
            # Close button
            close_button = ttk.Button(header_frame, text="×", width=3, 
                                    command=self.hide_web_panel)
            close_button.pack(side="right")
            
            # Notebook widget for tabs
            self.web_notebook = ttk.Notebook(self.web_frame)
            self.web_notebook.pack(fill="both", expand=True, padx=5, pady=(0, 5))
            
            # Add initial placeholder tab
            self.add_placeholder_tab()
    
    def add_placeholder_tab(self):
        """Add a placeholder tab when no word is selected"""
        if self.web_notebook:
            # Clear existing tabs
            for tab_id in self.web_notebook.tabs():
                self.web_notebook.forget(tab_id)
            
            # Create placeholder frame
            placeholder_frame = ttk.Frame(self.web_notebook)
            self.web_notebook.add(placeholder_frame, text="Selecione uma palavra")
            
            # Add content to placeholder
            try:
                placeholder_viewer = tkinterweb.HtmlFrame(placeholder_frame, messages_enabled=False)
                placeholder_viewer.pack(fill="both", expand=True, padx=10, pady=10)
                
                placeholder_html = """
                <html>
                <head>
                    <style>
                        body { 
                            font-family: 'Segoe UI', Arial, sans-serif; 
                            margin: 20px; 
                            text-align: center;
                            background-color: #f8f9fa;
                        }
                        h2 { color: #495057; margin-bottom: 15px; }
                        p { color: #6c757d; line-height: 1.6; }
                        .icon { font-size: 48px; margin-bottom: 15px; }
                    </style>
                </head>
                <body>
                    <div class="icon">📝</div>
                    <h2>Caracteres</h2>
                    <p>Clique em uma palavra chinesa no canvas para ver cada caractere em abas separadas.</p>
                    <p>Cada aba mostrará informações detalhadas sobre um caractere individual.</p>
                </body>
                </html>
                """
                placeholder_viewer.load_html(placeholder_html)
                
            except Exception as e:
                print(f"Error creating placeholder viewer: {e}")
                # Fallback to text widget
                text_widget = tk.Text(placeholder_frame, wrap="word", padx=15, pady=15)
                text_widget.pack(fill="both", expand=True)
                text_widget.insert("1.0", "Clique em uma palavra chinesa para analisar cada caractere individualmente.")
                text_widget.config(state="disabled")
    
    def show_web_panel(self, word_data):
        """Show the web panel with tabs for each character in the word"""
        if not self.web_panel_visible:
            # Add web frame to right pane of PanedWindow
            self.main_paned.add(self.web_frame, weight=3)
            # Note: User can resize as needed via sash dragging
            self.web_panel_visible = True
            
            # Restore previous sash position if available, otherwise set a good default
            if self.last_right_sash_position is not None:
                # Adjust sash position based on whether left panel is visible
                if self.word_panel_visible:
                    self.root.after_idle(lambda: self.main_paned.sashpos(1, self.last_right_sash_position))
                else:
                    self.root.after_idle(lambda: self.main_paned.sashpos(0, self.last_right_sash_position))
            else:
                # Set initial position to give about 80% to canvas, 20% to web panel
                self.root.after_idle(self._set_initial_right_sash_position)
        
        # Update the title
        if hasattr(self, 'web_title_label'):
            self.web_title_label.config(text=f"{word_data['word']}")
        
        # Clear existing tabs
        if self.web_notebook:
            for tab_id in self.web_notebook.tabs():
                self.web_notebook.forget(tab_id)
        
        # Split word into individual characters and create tabs
        word = word_data['word']
        characters = list(word)  # Split into individual characters
        
        print(f"Creating tabs for characters: {characters}")
        
        for i, character in enumerate(characters):
            self.create_character_tab(character, i, word_data)
    
    def create_character_tab(self, character, index, word_data):
        """Create a tab for an individual character"""
        if not self.web_notebook:
            return
        
        # Create frame for this character
        char_frame = ttk.Frame(self.web_notebook)
        
        # Add tab with character as title
        self.web_notebook.add(char_frame, text=f"{character}")
        
        # Create interface for this character with API integration
        char_url = f"https://stroke-order.learningweb.moe.edu.tw/searchW.jsp?ID2=1&WORD={character}"
        
        # Fetch character information from API
        character_data = self.fetch_character_info(character)
        
        # Create main content frame with scrollable text widget
        content_frame = ttk.Frame(char_frame)
        content_frame.pack(fill="both", expand=True, padx=5, pady=5)
        
        # Create text widget with scrollbar
        text_widget = tk.Text(content_frame, wrap="word", font=("Arial", 12), 
                            bg="white", fg="#212529", relief="solid", 
                            borderwidth=1, padx=15, pady=15)
        text_scrollbar = ttk.Scrollbar(content_frame, orient="vertical", command=text_widget.yview)
        text_widget.configure(yscrollcommand=text_scrollbar.set)
        
        # Pack text widget and scrollbar
        text_widget.pack(side="left", fill="both", expand=True)
        text_scrollbar.pack(side="right", fill="y")
        
        # Format and display character data
        text_widget.config(state="normal")  # Enable for insertion
        
        if character_data:
            # Character title
            text_widget.insert("end", f"{character}\n", "character")
            text_widget.insert("end", f"Frequência: {character_data.get('frequency', 'N/A')} | Consultas: {character_data.get('calls', 'N/A')}\n\n", "stats")
            
            # Decomposition (first, as requested)
            decomp = character_data.get('decomposition', 'N/A')
            decomp_meaning = character_data.get('decomposition_meaning', 'N/A')
            text_widget.insert("end", f"{decomp}\n", "decomp_title")
            text_widget.insert("end", f"{decomp_meaning}\n\n", "decomp_text")
            
            # Meaning - parse bold formatting
            meaning = character_data.get('meaning', 'N/A')
            self.insert_formatted_text(text_widget, meaning + "\n\n", "meaning")
            
            # Related words
            related = character_data.get('related_words', 'Nenhuma palavra relacionada encontrada')
            text_widget.insert("end", f"{related}\n\n", "related")
            
        else:
            text_widget.insert("end", f"{character}\n", "character")
            text_widget.insert("end", "⚠️ Informações da API não disponíveis\n\n", "error")
            text_widget.insert("end", "Verifique se a API está executando em http://localhost:7998", "info")
        
        # Configure text styles
        text_widget.tag_configure("character", font=("Arial", 36, "bold"), foreground="#2c3e50", justify="center")
        text_widget.tag_configure("stats", font=("Arial", 10), foreground="#6c757d", justify="center")
        text_widget.tag_configure("decomp_title", font=("Arial", 14, "bold"), foreground="#495057")
        text_widget.tag_configure("decomp_text", font=("Arial", 12), foreground="#212529")
        text_widget.tag_configure("meaning", font=("Arial", 12), foreground="#212529")
        text_widget.tag_configure("meaning_bold", font=("Arial", 12, "bold"), foreground="#495057")
        text_widget.tag_configure("related", font=("Arial", 11), foreground="#212529")
        text_widget.tag_configure("error", font=("Arial", 12, "bold"), foreground="#dc3545", justify="center")
        text_widget.tag_configure("info", font=("Arial", 10), foreground="#6c757d", justify="center")
        
        # Make all Chinese characters clickable
        try:
            self._make_text_chinese_clickable(text_widget)
        except Exception as e:
            print(f"Error tagging Chinese characters as clickable: {e}")
        
        # Make text widget read-only
        text_widget.config(state="disabled")
        
        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            text_widget.yview_scroll(int(-1*(event.delta/120)), "units")
        
        text_widget.bind("<MouseWheel>", _on_mousewheel)
        text_widget.bind("<Button-4>", _on_mousewheel)
        text_widget.bind("<Button-5>", _on_mousewheel)
        
        # Bind copy shortcut to copy the current character (Ctrl/Cmd + C)
        def _on_copy_shortcut(event):
            try:
                copy_character_to_clipboard()
            except Exception:
                pass
            return "break"
        text_widget.bind("<Control-c>", _on_copy_shortcut)
        text_widget.bind("<Command-c>", _on_copy_shortcut)
        
        # Separator frame for stroke order buttons
        button_frame = ttk.Frame(char_frame)
        button_frame.pack(fill="x", padx=10, pady=(5, 10))
        
        # Copy button for the current character
        def copy_character_to_clipboard():
            try:
                self.root.clipboard_clear()
                self.root.clipboard_append(character)
                # Visual feedback
                try:
                    copy_button.config(text="Copiado!")
                    self.root.after(800, lambda: copy_button.config(text="Copiar"))
                except Exception:
                    pass
            except Exception as e:
                print(f"Error copying character to clipboard: {e}")
        
        copy_button = ttk.Button(button_frame, text="Copiar", command=copy_character_to_clipboard)
        copy_button.pack(pady=2)
        
        # Add separator line
        separator = ttk.Separator(button_frame, orient="horizontal")
        separator.pack(fill="x", pady=(5, 10))
        
        # Label for stroke order section
        stroke_label = ttk.Label(button_frame, text="Ordem de Traços - Taiwan MOE", 
                               font=("Arial", 10, "bold"), foreground="#007bff")
        stroke_label.pack(pady=(0, 5))
        
        # Open webview window button
        def open_webview_window():
            try:
                # Check if window is already open
                window_key = f"webview_{character}"
                if window_key not in self.opened_windows:
                    # Create webview window using subprocess to avoid threading issues
                    try:
                        # Path to helper script
                        helper_script = os.path.join(os.path.dirname(__file__), "webview_helper.py")
                        
                        print(f"Attempting to launch webview for {character}")
                        print(f"Helper script path: {helper_script}")
                        print(f"URL: {char_url}")
                        
                        # Launch webview in separate process with better error handling
                        process = subprocess.Popen([
                            sys.executable,
                            helper_script,
                            f"Caractere: {character}",
                            char_url
                        ], 
                        stdout=subprocess.PIPE, 
                        stderr=subprocess.PIPE,
                        text=True)
                        
                        # Mark window as opened
                        self.opened_windows[window_key] = process
                        
                        # Monitor process in background to check for errors and clean up
                        def monitor_process():
                            try:
                                stdout, stderr = process.communicate(timeout=2)
                                if process.returncode != 0:
                                    print(f"Webview process failed for {character}")
                                    print(f"Return code: {process.returncode}")
                                    if stderr:
                                        print(f"Error output: {stderr}")
                                    # Fallback to browser if webview fails
                                    self.root.after_idle(lambda: webbrowser.open(char_url))
                                else:
                                    print(f"Webview window opened successfully for character {character}")
                            except subprocess.TimeoutExpired:
                                # Process is still running (good for webview)
                                print(f"Webview window for {character} is running")
                                # Continue monitoring until process ends
                                process.wait()
                            except Exception as e:
                                print(f"Error monitoring webview process: {e}")
                            finally:
                                if window_key in self.opened_windows:
                                    del self.opened_windows[window_key]
                        
                        monitor_thread = threading.Thread(target=monitor_process, daemon=True)
                        monitor_thread.start()
                        
                    except Exception as e:
                        print(f"Error creating webview subprocess: {e}")
                        # Fallback to browser
                        webbrowser.open(char_url)
                        
                else:
                    print(f"Window for character {character} is already open")
            except Exception as e:
                print(f"Error opening webview window: {e}")
                # Fallback to browser
                webbrowser.open(char_url)
        
        # Open Safari window with AppleScript (more reliable on macOS)
        def open_safari_window():
            try:
                # Use AppleScript to open Safari in a new window
                applescript = f'''
                tell application "Safari"
                    activate
                    make new document with properties {{URL:"{char_url}"}}
                    set bounds of front window to {{100, 100, 900, 700}}
                end tell
                '''
                
                subprocess.run(['osascript', '-e', applescript], check=True)
                print(f"Opened Safari window for character {character}: {char_url}")
            except Exception as e:
                print(f"Error opening Safari window: {e}")
                # Final fallback to default browser
                webbrowser.open(char_url)
        
        # Open webview button (primary)
        webview_button = ttk.Button(button_frame, text="Abrir Janela de Traços", 
                                   command=open_webview_window)
        webview_button.pack(pady=2)
        
        # Safari button (alternative)
        safari_button = ttk.Button(button_frame, text="Abrir no Safari", 
                                  command=open_safari_window)
        safari_button.pack(pady=2)
        
        
        # Status message
        status_label = ttk.Label(button_frame, 
                               text="Use 'Janela de Traços' (webview) ou 'Safari' para visualizar a ordem dos traços", 
                               font=("Arial", 9), foreground="#868e96", wraplength=250)
        status_label.pack(pady=(5, 0))
    
    def fetch_word_info(self, word):
        """Fetch word information from the word-api"""
        try:
            # URL encode the word for the API call
            encoded_word = urllib.parse.quote(word, safe='')
            api_url = f"http://localhost:7998/word-api/{encoded_word}"
            
            print(f"Fetching word info for: {word} from {api_url}")
            
            # Make API request with timeout
            response = requests.get(api_url, timeout=5)
            response.raise_for_status()  # Raise exception for bad status codes
            
            # Parse JSON response
            word_data = response.json()
            
            return word_data
            
        except requests.exceptions.Timeout:
            print(f"Timeout fetching data for word: {word}")
            return None
        except requests.exceptions.ConnectionError:
            print(f"Connection error fetching data for word: {word}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data for word {word}: {e}")
            return None
        except ValueError as e:
            print(f"Error parsing JSON response for word {word}: {e}")
            return None

    def search_related_words(self, query):
        """Search for related words using the word-api search endpoint"""
        try:
            # URL encode the query for the API call
            encoded_query = urllib.parse.quote(query, safe='')
            api_url = f"http://localhost:7998/word-api/search?q={encoded_query}"
            
            print(f"Searching related words for: {query} from {api_url}")
            
            # Make API request with timeout
            response = requests.get(api_url, timeout=5)
            response.raise_for_status()  # Raise exception for bad status codes
            
            # Parse JSON response
            search_results = response.json()
            
            return search_results
            
        except requests.exceptions.Timeout:
            print(f"Timeout searching for: {query}")
            return []
        except requests.exceptions.ConnectionError:
            print(f"Connection error searching for: {query}")
            return []
        except requests.exceptions.RequestException as e:
            print(f"Error searching for {query}: {e}")
            return []
        except ValueError as e:
            print(f"Error parsing JSON response for search {query}: {e}")
            return []

    def fetch_character_info(self, character):
        """Fetch character information from the hanzi API"""
        try:
            # URL encode the character for the API call
            encoded_char = urllib.parse.quote(character, safe='')
            api_url = f"http://localhost:7998/hanzi-api/hanzi/{encoded_char}"
            
            print(f"Fetching character info for: {character} from {api_url}")
            
            # Make API request with timeout
            response = requests.get(api_url, timeout=5)
            response.raise_for_status()  # Raise exception for bad status codes
            
            # Parse JSON response
            character_data = response.json()
            
            # Check if meaning and decomposition fields are missing or empty
            needs_enrichment = (
                not character_data.get('meaning') or 
                not character_data.get('decomposition')
            )
            
            if needs_enrichment:
                print(f"Character {character} needs enrichment - calling enrich endpoint")
                
                # Call enrichment endpoint
                enrich_url = f"http://localhost:7998/hanzi-api/hanzi/{encoded_char}/enrich"
                try:
                    enrich_response = requests.put(enrich_url, timeout=10)
                    enrich_response.raise_for_status()
                    print(f"Enrichment successful for character: {character}")
                    
                    # Fetch updated character data after enrichment
                    updated_response = requests.get(api_url, timeout=5)
                    updated_response.raise_for_status()
                    
                    character_data = updated_response.json()
                    print(f"Updated API response for {character}: {character_data}")
                    
                except requests.exceptions.RequestException as enrich_error:
                    print(f"Error enriching character {character}: {enrich_error}")
                    # Continue with original data if enrichment fails
            
            return character_data
            
        except requests.exceptions.Timeout:
            print(f"Timeout fetching data for character: {character}")
            return None
        except requests.exceptions.ConnectionError:
            print(f"Connection error fetching data for character: {character}")
            return None
        except requests.exceptions.RequestException as e:
            print(f"Error fetching data for character {character}: {e}")
            return None
        except ValueError as e:
            print(f"Error parsing JSON response for character {character}: {e}")
            return None
    
    def insert_formatted_text(self, text_widget, text, base_tag):
        """Insert text with bold formatting for **text** patterns"""
        import re
        
        # Find all bold patterns
        bold_pattern = r'\*\*(.*?)\*\*'
        parts = re.split(bold_pattern, text)
        
        for i, part in enumerate(parts):
            if i % 2 == 0:
                # Regular text
                if part:
                    text_widget.insert("end", part, base_tag)
            else:
                # Bold text (between ** **)
                if part:
                    text_widget.insert("end", part, f"{base_tag}_bold")
    
    def _is_chinese_char(self, ch: str) -> bool:
        """Return True if character is a CJK ideograph or related extension."""
        if not ch:
            return False
        code = ord(ch)
        # Basic CJK Unified Ideographs
        if 0x4E00 <= code <= 0x9FFF:
            return True
        # CJK Unified Ideographs Extension A
        if 0x3400 <= code <= 0x4DBF:
            return True
        # CJK Compatibility Ideographs
        if 0xF900 <= code <= 0xFAFF:
            return True
        # CJK Unified Ideographs Extensions B..G (surrogates range)
        if 0x20000 <= code <= 0x3134F:
            return True
        return False

    def _make_text_chinese_clickable(self, text_widget: tk.Text) -> None:
        """Scan the text widget, tag all continuous Chinese sequences and bind click handler."""
        # Ensure tag exists and set optional visual cue
        try:
            text_widget.tag_configure("hanzi_click", underline=0)
        except Exception:
            pass
        content = text_widget.get("1.0", "end-1c")
        line = 1
        col = 0
        run_start = None  # tuple(line, col)
        for ch in content:
            if ch == "\n":
                # Close any open run before line break
                if run_start is not None:
                    start_idx = f"{run_start[0]}.{run_start[1]}"
                    end_idx = f"{line}.{col}"
                    text_widget.tag_add("hanzi_click", start_idx, end_idx)
                    run_start = None
                line += 1
                col = 0
                continue
            if self._is_chinese_char(ch):
                if run_start is None:
                    run_start = (line, col)
            else:
                if run_start is not None:
                    start_idx = f"{run_start[0]}.{run_start[1]}"
                    end_idx = f"{line}.{col}"
                    text_widget.tag_add("hanzi_click", start_idx, end_idx)
                    run_start = None
            col += 1
        # Close final run at EOF
        if run_start is not None:
            start_idx = f"{run_start[0]}.{run_start[1]}"
            end_idx = f"{line}.{col}"
            try:
                text_widget.tag_add("hanzi_click", start_idx, end_idx)
            except Exception:
                pass

        # Bind click behavior and hover cursor on tagged regions
        def on_hanzi_click(event):
            try:
                index = event.widget.index(f"@{event.x},{event.y}")
                word = self._extract_chinese_sequence_at(event.widget, index)
                if word and word.strip():
                    self.add_word_to_canvas(word.strip())
            except Exception as e:
                print(f"Error handling hanzi click: {e}")

        text_widget.tag_bind("hanzi_click", "<Button-1>", on_hanzi_click)
        text_widget.tag_bind("hanzi_click", "<Enter>", lambda e: e.widget.config(cursor="hand2"))
        text_widget.tag_bind("hanzi_click", "<Leave>", lambda e: e.widget.config(cursor="xterm"))

    def _extract_chinese_sequence_at(self, text_widget: tk.Text, index: str) -> str:
        """Return the full contiguous Chinese sequence around the given index."""
        try:
            # If current char is not Chinese, return empty
            ch = text_widget.get(index, f"{index} +1c")
            if not ch or not self._is_chinese_char(ch):
                return ""
            # Expand left
            start_idx = index
            while True:
                prev_idx = text_widget.index(f"{start_idx} -1c")
                prev_ch = text_widget.get(prev_idx, f"{prev_idx} +1c")
                if not prev_ch or not self._is_chinese_char(prev_ch) or prev_idx == start_idx:
                    break
                start_idx = prev_idx
            # Expand right
            end_idx = text_widget.index(f"{index} +1c")
            while True:
                next_ch = text_widget.get(end_idx, f"{end_idx} +1c")
                if not next_ch or not self._is_chinese_char(next_ch):
                    break
                end_idx = text_widget.index(f"{end_idx} +1c")
            return text_widget.get(start_idx, end_idx)
        except Exception:
            return ""

    def add_word_to_canvas(self, word: str, size: int = 36) -> None:
        """Add a new word to the canvas near the selected word or viewport center and persist to CSV."""
        # Compute insertion position
        try:
            if (
                self.selected_word_id is not None and 
                self.selected_word_id in self.word_objects and 
                0 <= int(self.selected_word_id) < len(self.words_data)
            ):
                base = self.words_data[self.selected_word_id]
                base_x = base['position']['x']
                base_y = base['position']['y']
                x = int(base_x + max(40, base['size'] + 20))
                y = int(base_y)
            else:
                # Center of current viewport
                sr = self.canvas.cget("scrollregion") or "0 0 2000 2000"
                parts = [int(float(p)) for p in sr.split()] if isinstance(sr, str) else [0, 0, 2000, 2000]
                x1, y1, x2, y2 = parts if len(parts) == 4 else (0, 0, 2000, 2000)
                xv = self.canvas.xview()
                yv = self.canvas.yview()
                vis_left = x1 + (x2 - x1) * (xv[0] if xv else 0.0)
                vis_right = x1 + (x2 - x1) * (xv[1] if xv else 1.0)
                vis_top = y1 + (y2 - y1) * (yv[0] if yv else 0.0)
                vis_bottom = y1 + (y2 - y1) * (yv[1] if yv else 1.0)
                x = int((vis_left + vis_right) / 2)
                y = int((vis_top + vis_bottom) / 2)
        except Exception:
            x, y = 100, 100

        # Create data entry
        new_word = {
            'word': word,
            'size': size,
            'position': {'x': x, 'y': y},
            'hasPinyin': False,
            'hasTranslation': False,
            'pinyin': '',
            'translation': '',
            'tonePair': ''
        }
        # Append to data and draw just this word
        new_id = len(self.words_data)
        self.words_data.append(new_word)

        text_ids, outline_ids = self.draw_word_with_tones(new_id, x, y, word, size, '')
        self.word_objects[new_id] = {
            'text_id': text_ids[0] if text_ids else None,
            'text_ids': text_ids,
            'outline_ids': outline_ids,
            'pinyin_text_id': None,
            'pinyin_text_ids': [],
            'pinyin_outline_ids': [],
            'translation_text_id': None,
            'translation_outline_ids': [],
            'selection_rect_id': None,
            'data': new_word
        }
        # Persist to CSV and update scroll region
        self.update_scroll_region()
        self.save_positions()
        # Select the newly added word to keep selection in sync
        try:
            self.select_word(new_id)
        except Exception:
            pass
    
    def format_character_data_html(self, character, character_data):
        """Format character data into HTML for display"""
        if not character_data:
            return f"""
            <html>
            <head>
                <style>
                    body {{ 
                        font-family: 'Segoe UI', Arial, sans-serif; 
                        margin: 15px; 
                        background-color: #f8f9fa;
                        line-height: 1.6;
                    }}
                    .character {{ 
                        font-size: 48px; 
                        font-weight: bold; 
                        text-align: center; 
                        color: #2c3e50; 
                        margin: 15px 0;
                    }}
                    .error {{
                        text-align: center;
                        color: #dc3545;
                        background-color: #f8d7da;
                        border: 1px solid #f5c6cb;
                        border-radius: 5px;
                        padding: 10px;
                        margin: 10px 0;
                    }}
                    .info {{
                        color: #6c757d;
                        font-size: 14px;
                        text-align: center;
                    }}
                </style>
            </head>
            <body>
                <div class="character">{character}</div>
                <div class="error">
                    ⚠️ Informações não disponíveis
                </div>
                <div class="info">
                    Verifique se a API está executando em http://localhost:7998
                </div>
            </body>
            </html>
            """
        
        # Format the data into HTML
        html_content = f"""
        <html>
        <head>
            <style>
                body {{ 
                    font-family: 'Segoe UI', Arial, sans-serif; 
                    margin: 15px; 
                    background-color: #f8f9fa;
                    line-height: 1.6;
                }}
                .character {{ 
                    font-size: 48px; 
                    font-weight: bold; 
                    text-align: center; 
                    color: #2c3e50; 
                    margin: 15px 0;
                }}
                .section {{
                    margin: 15px 0;
                    padding: 12px;
                    background-color: white;
                    border-radius: 8px;
                    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
                }}
                .content {{
                    color: #212529;
                    font-size: 14px;
                }}
                .stats {{
                    display: flex;
                    justify-content: space-between;
                    background-color: #e9ecef;
                    padding: 8px;
                    border-radius: 5px;
                    font-size: 12px;
                    color: #6c757d;
                }}
                .related-words {{
                    font-family: 'Segoe UI', Arial, sans-serif;
                    white-space: pre-line;
                }}
                .decomposition {{
                    font-weight: bold;
                }}
            </style>
        </head>
        <body>
            <div class="character">{character}</div>
            
            <div class="stats">
                <span>Frequência: {character_data.get('frequency', 'N/A')}</span>
                <span>Consultas: {character_data.get('calls', 'N/A')}</span>
            </div>
            
            <div class="section">
                <div class="content">
                    <span class="decomposition">{character_data.get('decomposition', 'N/A')}</span><br>
                    {character_data.get('decomposition_meaning', 'Informação não disponível')}
                </div>
            </div>
            
            <div class="section">
                <div class="content">{character_data.get('meaning', 'Informação não disponível')}</div>
            </div>
            
            <div class="section">
                <div class="content related-words">{character_data.get('related_words', 'Nenhuma palavra relacionada encontrada')}</div>
            </div>
        </body>
        </html>
        """
        
        return html_content
    
    def hide_web_panel(self):
        """Hide the web panel"""
        if self.web_panel_visible:
            # Save current sash position before hiding
            try:
                # Adjust sash position based on whether left panel is visible
                if self.word_panel_visible:
                    self.last_right_sash_position = self.main_paned.sashpos(1)
                else:
                    self.last_right_sash_position = self.main_paned.sashpos(0)
            except tk.TclError:
                # No sash position available
                pass
            
            # Remove web frame from PanedWindow
            self.main_paned.remove(self.web_frame)
            self.web_panel_visible = False
    
    def _set_initial_right_sash_position(self):
        """Set initial right sash position to give reasonable split between canvas and web panel"""
        try:
            window_width = self.root.winfo_width()
            if window_width > 100:  # Make sure window is properly sized
                # Position at about 80% of window width
                sash_pos = int(window_width * 0.8)
                # Adjust sash position based on whether left panel is visible
                if self.word_panel_visible:
                    self.main_paned.sashpos(1, sash_pos)
                else:
                    self.main_paned.sashpos(0, sash_pos)
        except (tk.TclError, AttributeError):
            # Fallback if there's any issue
            pass
    
        
    def load_words_from_csv(self, csv_path: Optional[str] = None):
        """Load words from a CSV file. Uses current CSV if path not provided."""
        csv_path = os.path.abspath(csv_path or self.current_csv_path)
        # Keep the absolute path stored to avoid accidental relative writes
        self.current_csv_path = csv_path
        
        try:
            self.words_data = []
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    # Skip empty rows
                    word_raw = row.get('word')
                    if not word_raw or (isinstance(word_raw, str) and not word_raw.strip()):
                        continue
                        
                    # Convert float strings to int for positions
                    try:
                        position_x_raw = row.get('position_x', 0)
                        position_y_raw = row.get('position_y', 0)
                        size_raw = row.get('size', 36)
                        position_x = int(float(position_x_raw or 0))
                        position_y = int(float(position_y_raw or 0))
                        size = int(float(size_raw or 36))
                    except (ValueError, KeyError) as e:
                        print(f"Error parsing numeric values for word '{row.get('word', 'unknown')}': {e}")
                        continue
                    
                    # Safe coercions
                    def to_str(value):
                        if value is None:
                            return ''
                        return value.strip() if isinstance(value, str) else str(value).strip()
                    def to_bool(value):
                        return str(value).strip().lower() == 'true'

                    word_data = {
                        'word': to_str(row.get('word')),
                        'size': size,
                        'position': {
                            'x': position_x,
                            'y': position_y
                        },
                        'hasPinyin': to_bool(row.get('has_pinyin', 'false')),
                        'hasTranslation': to_bool(row.get('has_translation', 'false')),
                        'pinyin': to_str(row.get('pinyin')),
                        'translation': to_str(row.get('translation')),
                        'tonePair': to_str(row.get('tone_pair'))
                    }
                    self.words_data.append(word_data)
            
            print(f"Loaded {len(self.words_data)} words from CSV: {csv_path}")
            
        except FileNotFoundError:
            messagebox.showerror("Error", f"CSV file not found: {csv_path}")
        except Exception as e:
            messagebox.showerror("Error", f"Error loading CSV: {str(e)}")
            print(f"Detailed error: {e}")  # Print to console for debugging
    
    def draw_words(self):
        """Draw all words on the canvas"""
        self.canvas.delete("all")
        self.word_objects = {}
        
        for i, word_data in enumerate(self.words_data):
            x = word_data['position']['x']
            y = word_data['position']['y']
            word = word_data['word']
            size = word_data['size']
            tone_pair = word_data.get('tonePair', '')

            text_ids, outline_ids = self.draw_word_with_tones(i, x, y, word, size, tone_pair)

            # Store word object data
            self.word_objects[i] = {
                'text_id': text_ids[0] if text_ids else None,
                'text_ids': text_ids,
                'outline_ids': outline_ids,
                'pinyin_text_id': None,
                'pinyin_outline_ids': [],
                'translation_text_id': None,
                'translation_outline_ids': [],
                'selection_rect_id': None,  # Will be created when selected
                'data': word_data
            }
            
            # Add pinyin text if enabled
            if word_data.get('hasPinyin') and word_data.get('pinyin'):
                self.draw_pinyin_for_word(i, x, y - size - 5, word_data['pinyin'], int(size * 0.5))
            
            # Add translation text if enabled
            if word_data.get('hasTranslation') and word_data.get('translation'):
                self.draw_translation_for_word(i, x, y + size + 10, word_data['translation'], int(size * 0.5))
        
        # Update scroll region to fit all content
        self.update_scroll_region()
    
    def draw_pinyin_for_word(self, word_id: int, x: int, y: int, pinyin: str, size: int):
        """Draw pinyin text above the main word. If tone information is available,
        color each pinyin syllable to match its corresponding character color.
        """
        # Clear any existing pinyin items for this word to avoid overlapping layers
        try:
            self.canvas.delete(f"word_{word_id}_pinyin")
            self.canvas.delete(f"word_{word_id}_pinyin_outline")
        except Exception:
            pass

        word_data = self.words_data[word_id] if 0 <= int(word_id) < len(self.words_data) else None
        tone_pair = (word_data.get('tonePair') if isinstance(word_data, dict) else '') or ''
        word_text = (word_data.get('word') if isinstance(word_data, dict) else '') or ''

        # Tone to color mapping (same as characters)
        tone_to_color = {
            '1': '#90ee90',  # light green
            '2': '#add8e6',  # light blue
            '3': '#d2b48c',  # tan (light brown)
            '4': '#ffc0cb',  # pink
            '5': '#d3d3d3',  # light gray
        }

        # Prepare syllables and tones
        syllables = [s for s in (pinyin or '').split() if s]
        tones = [ch for ch in (tone_pair or '') if ch in '12345']
        chars = list(word_text)

        can_color_per_syllable = bool(chars) and bool(syllables)

        # If we can map syllables to characters, align each syllable to its character center
        if can_color_per_syllable:
            # Use main word size for measuring character positions
            main_size = int(word_data.get('size') or 0) if isinstance(word_data, dict) else 0
            try:
                canvas_font = tkfont.Font(family="Arial", size=main_size, weight="bold")
                total_width = canvas_font.measure(word_text)
            except Exception:
                total_width = 0

            if total_width > 0:
                left_edge = x - total_width / 2
                # Precompute centers for each character
                char_centers = []
                for idx, ch in enumerate(chars):
                    prefix = word_text[:idx]
                    prefix_width = canvas_font.measure(prefix)
                    char_width = canvas_font.measure(ch)
                    char_center_x = left_edge + prefix_width + (char_width / 2)
                    char_centers.append(int(char_center_x))

                # Map counts
                count = min(len(chars), len(syllables))

                # Try to read actual colors from already drawn characters (most reliable)
                char_drawn_colors = []
                try:
                    word_obj = self.word_objects.get(word_id, {})
                    drawn_text_ids = word_obj.get('text_ids') or []
                    for tid in drawn_text_ids:
                        try:
                            char_drawn_colors.append(self.canvas.itemcget(tid, 'fill'))
                        except Exception:
                            char_drawn_colors.append('white')
                except Exception:
                    char_drawn_colors = []

                # Compute a single adjusted font size for all syllables so that
                # every syllable fits within its corresponding character width
                try:
                    base_syll_font = tkfont.Font(family="Arial", size=size, weight="bold")
                    char_widths_px = [canvas_font.measure(ch) for ch in chars[:count]]
                    syll_widths_px = [base_syll_font.measure(s) for s in syllables[:count]]
                    scales = []
                    for i in range(count):
                        allowed = char_widths_px[i] * 0.9  # leave small margin
                        w = max(1, syll_widths_px[i])
                        scales.append(allowed / w)
                    scale_all = min(scales) if scales else 1.0
                    scale_all = max(0.6, min(1.0, scale_all))
                    adj_size_common = max(8, int(size * scale_all))
                except Exception:
                    adj_size_common = size

                pinyin_outline_ids: list[int] = []
                pinyin_text_ids: list[int] = []

                for i in range(count):
                    syll = syllables[i]
                    # Prefer actual drawn color if available, fallback to tone mapping, else white
                    if i < len(char_drawn_colors) and char_drawn_colors[i]:
                        color = char_drawn_colors[i]
                    else:
                        tone_fallback = tones[i] if i < len(tones) else None
                        color = tone_to_color.get(tone_fallback, 'white')
                    cx = char_centers[i] if i < len(char_centers) else x

                    adj_size = adj_size_common

                    # Outline for the syllable
                    for dx in [-2, -1, 0, 1, 2]:
                        for dy in [-2, -1, 0, 1, 2]:
                            if dx != 0 or dy != 0:
                                outline_id = self.canvas.create_text(
                                    int(cx + dx), int(y + dy),
                                    text=syll,
                                    font=("Arial", adj_size, "bold"),
                                    fill="black",
                                    tags=f"word_{word_id}_pinyin_outline"
                                )
                                pinyin_outline_ids.append(outline_id)

                    # Main colored syllable
                    text_id = self.canvas.create_text(
                        int(cx), y,
                        text=syll,
                        font=("Arial", adj_size, "bold"),
                        fill=color,
                        tags=f"word_{word_id}_pinyin"
                    )
                    pinyin_text_ids.append(text_id)

                # Store IDs (keep first text id as primary for bbox queries)
                self.word_objects[word_id]['pinyin_text_id'] = (pinyin_text_ids[0] if pinyin_text_ids else None)
                self.word_objects[word_id]['pinyin_text_ids'] = pinyin_text_ids
                self.word_objects[word_id]['pinyin_outline_ids'] = pinyin_outline_ids
                return

        # Fallback: draw single white pinyin centered if mapping not possible
        pinyin_outline_ids = []
        for dx in [-2, -1, 0, 1, 2]:
            for dy in [-2, -1, 0, 1, 2]:
                if dx != 0 or dy != 0:
                    outline_id = self.canvas.create_text(
                        x + dx, y + dy,
                        text=pinyin,
                        font=("Arial", max(8, int(size * 0.9)), "bold"),
                        fill="black",
                        tags=f"word_{word_id}_pinyin_outline"
                    )
                    pinyin_outline_ids.append(outline_id)

        pinyin_text_id = self.canvas.create_text(
            x, y,
            text=pinyin,
            font=("Arial", max(8, int(size * 0.9)), "bold"),
            fill="white",
            tags=f"word_{word_id}_pinyin"
        )

        self.word_objects[word_id]['pinyin_text_id'] = pinyin_text_id
        self.word_objects[word_id]['pinyin_text_ids'] = [pinyin_text_id]
        self.word_objects[word_id]['pinyin_outline_ids'] = pinyin_outline_ids
    
    def draw_translation_for_word(self, word_id: int, x: int, y: int, translation: str, size: int):
        """Draw translation text below the main word"""
        # Create translation outline
        translation_outline_ids = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx != 0 or dy != 0:
                    outline_id = self.canvas.create_text(
                        x + dx, y + dy,
                        text=translation,
                        font=("Arial", size, "normal"),
                        fill="black",
                        tags=f"word_{word_id}_translation_outline"
                    )
                    translation_outline_ids.append(outline_id)
        
        # Create main translation text
        translation_text_id = self.canvas.create_text(
            x, y,
            text=translation,
            font=("Arial", size, "normal"),
            fill="#ffff99",
            tags=f"word_{word_id}_translation"
        )
        
        # Store IDs
        self.word_objects[word_id]['translation_text_id'] = translation_text_id
        self.word_objects[word_id]['translation_outline_ids'] = translation_outline_ids
    
    def on_canvas_click(self, event):
        """Handle mouse click on canvas"""
        # Convert event coordinates to canvas coordinates (accounting for scroll)
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Get all items at the clicked position
        items_at_position = self.canvas.find_overlapping(canvas_x-1, canvas_y-1, canvas_x+1, canvas_y+1)
        
        # Find which word was clicked by checking if any of the items belongs to a word
        clicked_word_id = None
        for word_id, word_obj in self.word_objects.items():
            # Collect all text and outlines created for the word
            text_ids = []
            if word_obj.get('text_id'):
                text_ids.append(word_obj['text_id'])
            text_ids.extend(word_obj.get('text_ids', []))
            word_items = text_ids + word_obj['outline_ids']
            
            # Add pinyin items if they exist
            if word_obj.get('pinyin_text_id'):
                word_items.append(word_obj['pinyin_text_id'])
                word_items.extend(word_obj.get('pinyin_outline_ids', []))
            
            # Add translation items if they exist
            if word_obj.get('translation_text_id'):
                word_items.append(word_obj['translation_text_id'])
                word_items.extend(word_obj.get('translation_outline_ids', []))
            
            # Add selection rectangle if it exists
            if word_obj.get('selection_rect_id'):
                word_items.append(word_obj['selection_rect_id'])
            
            # Check if any of the clicked items belong to this word
            if any(item in items_at_position for item in word_items):
                clicked_word_id = word_id
                break
        
        if clicked_word_id is not None:
            self.select_word(clicked_word_id)
            self.drag_data = {
                "x": canvas_x,
                "y": canvas_y,
                "item": clicked_word_id
            }
        else:
            # Clicked on empty area - deselect all words
            self.clear_selection()
    
    def on_canvas_drag(self, event):
        """Handle mouse drag on canvas"""
        if self.drag_data["item"] is not None:
            # Convert event coordinates to canvas coordinates (accounting for scroll)
            canvas_x = self.canvas.canvasx(event.x)
            canvas_y = self.canvas.canvasy(event.y)
            
            # Calculate movement
            dx = canvas_x - self.drag_data["x"]
            dy = canvas_y - self.drag_data["y"]
            
            if dx != 0 or dy != 0:  # Only move if there's actual movement
                # Move the word (text, outline, and selection box)
                word_id = self.drag_data["item"]
                self.canvas.move(f"word_{word_id}", dx, dy)
                self.canvas.move(f"word_{word_id}_outline", dx, dy)
                self.canvas.move(f"word_{word_id}_selection", dx, dy)
                # Move pinyin and translation elements
                self.canvas.move(f"word_{word_id}_pinyin", dx, dy)
                self.canvas.move(f"word_{word_id}_pinyin_outline", dx, dy)
                self.canvas.move(f"word_{word_id}_translation", dx, dy)
                self.canvas.move(f"word_{word_id}_translation_outline", dx, dy)
                
                # Update position in data
                self.words_data[word_id]['position']['x'] += dx
                self.words_data[word_id]['position']['y'] += dy
                
                # Update scroll region to include new position
                self.update_scroll_region()
                
                # Update drag data with canvas coordinates
                self.drag_data["x"] = canvas_x
                self.drag_data["y"] = canvas_y
    
    def on_canvas_release(self, event):
        """Handle mouse release on canvas"""
        if self.drag_data["item"] is not None:
            # Auto-save positions when dragging ends
            self.save_positions()
        self.drag_data["item"] = None
    
    def select_word(self, word_id: int):
        """Select a word and highlight it"""
        # Guard against invalid ids
        if word_id not in self.word_objects or not (0 <= int(word_id) < len(self.words_data)):
            return
        self.clear_selection()
        self.selected_word_id = word_id
        
        # Highlight selected word with selection box
        word_obj = self.word_objects[word_id]
        
        # Get bounding box of main word (consider multiple text ids if present)
        bbox = None
        main_ids = []
        if word_obj.get('text_id'):
            main_ids.append(word_obj['text_id'])
        main_ids.extend(word_obj.get('text_ids', []))
        for tid in main_ids:
            tb = self.canvas.bbox(tid)
            if tb:
                if bbox is None:
                    bbox = list(tb)
                else:
                    bbox[0] = min(bbox[0], tb[0])
                    bbox[1] = min(bbox[1], tb[1])
                    bbox[2] = max(bbox[2], tb[2])
                    bbox[3] = max(bbox[3], tb[3])
        if bbox:
            min_x, min_y, max_x, max_y = bbox
            
            # Expand bounding box to include pinyin if visible
            if word_obj.get('pinyin_text_id'):
                pinyin_bbox = self.canvas.bbox(word_obj['pinyin_text_id'])
                if pinyin_bbox:
                    min_x = min(min_x, pinyin_bbox[0])
                    min_y = min(min_y, pinyin_bbox[1])
                    max_x = max(max_x, pinyin_bbox[2])
                    max_y = max(max_y, pinyin_bbox[3])
            
            # Expand bounding box to include translation if visible
            if word_obj.get('translation_text_id'):
                translation_bbox = self.canvas.bbox(word_obj['translation_text_id'])
                if translation_bbox:
                    min_x = min(min_x, translation_bbox[0])
                    min_y = min(min_y, translation_bbox[1])
                    max_x = max(max_x, translation_bbox[2])
                    max_y = max(max_y, translation_bbox[3])
            
            # Create selection rectangle around the complete word group (word + pinyin + translation)
            selection_rect_id = self.canvas.create_rectangle(
                min_x - 5, min_y - 5,
                max_x + 5, max_y + 5,
                outline="blue",
                width=2,
                fill="",
                dash=(5, 5),  # Dashed line pattern
                tags=f"word_{word_id}_selection"
            )
            # Move rectangle behind all text elements
            self.canvas.tag_lower(selection_rect_id, word_obj['text_id'])
            if word_obj.get('pinyin_text_id'):
                self.canvas.tag_lower(selection_rect_id, word_obj['pinyin_text_id'])
            if word_obj.get('translation_text_id'):
                self.canvas.tag_lower(selection_rect_id, word_obj['translation_text_id'])
            
            word_obj['selection_rect_id'] = selection_rect_id
        
        # Show both panels with word information
        try:
            if 0 <= int(word_id) < len(self.words_data):
                word_data = self.words_data[word_id]
                # Show left panel with word info and related words
                self.show_word_panel(word_data)
                # Show right panel with character tabs
                self.show_web_panel(word_data)
        except Exception:
            pass
    
    def clear_selection(self):
        """Clear word selection"""
        if self.selected_word_id is not None:
            try:
                if self.selected_word_id in self.word_objects:
                    word_obj = self.word_objects[self.selected_word_id]
                    if word_obj.get('selection_rect_id'):
                        self.canvas.delete(word_obj['selection_rect_id'])
                        word_obj['selection_rect_id'] = None
            except Exception:
                pass
            self.selected_word_id = None
    
    def save_positions(self):
        """Save current positions back to the current CSV file"""
        csv_path = os.path.abspath(self.current_csv_path)
        
        try:
            # Ensure directory exists
            dir_path = os.path.dirname(csv_path)
            if dir_path and not os.path.isdir(dir_path):
                os.makedirs(dir_path, exist_ok=True)
            print(f"Salvando CSV em: {csv_path}")
            with open(csv_path, 'w', encoding='utf-8', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['word', 'size', 'position_x', 'position_y', 'has_pinyin', 'has_translation', 'pinyin', 'translation', 'tone_pair'])
                
                for word_data in self.words_data:
                    writer.writerow([
                        word_data['word'],
                        word_data['size'],
                        word_data['position']['x'],
                        word_data['position']['y'],
                        str(word_data['hasPinyin']).lower(),
                        str(word_data['hasTranslation']).lower(),
                        word_data.get('pinyin', ''),
                        word_data.get('translation', ''),
                        word_data.get('tonePair', '')
                    ])
            
        except Exception as e:
            print(f"Error saving CSV: {str(e)}")
    
    def _on_mousewheel(self, event):
        """Handle mouse wheel scrolling"""
        # Scroll vertically
        self.canvas.yview_scroll(int(-1*(event.delta/120)), "units")
    
    def update_scroll_region(self):
        """Update scroll region to fit all content"""
        bbox = self.canvas.bbox("all")
        if bbox:
            # Add some padding around the content
            padding = 50
            self.canvas.configure(scrollregion=(
                bbox[0] - padding, 
                bbox[1] - padding, 
                bbox[2] + padding, 
                bbox[3] + padding
            ))
        else:
            # Default scroll region if no content
            self.canvas.configure(scrollregion=(0, 0, 2000, 2000))

    def draw_word_with_tones(self, word_id: int, x: int, y: int, word: str, size: int, tone_pair: str):
        """Draw a word with per-character coloring based on tone pairs.
        Returns (text_ids, outline_ids). Uses tags word_{id} and word_{id}_outline.
        """
        # Color mapping per tone number
        tone_to_color = {
            '1': '#90ee90',  # light green
            '2': '#add8e6',  # light blue
            '3': '#d2b48c',  # tan (light brown)
            '4': '#ffc0cb',  # pink
            '5': '#d3d3d3',  # light gray
        }

        # If tone_pair empty or length mismatch, fallback to single-color logic
        if not tone_pair or not word:
            outline_ids = []
            for dx in [-2, -1, 0, 1, 2]:
                for dy in [-2, -1, 0, 1, 2]:
                    if dx != 0 or dy != 0:
                        outline_id = self.canvas.create_text(
                            x + dx, y + dy,
                            text=word,
                            font=("Arial", size, "bold"),
                            fill="black",
                            tags=f"word_{word_id}_outline"
                        )
                        outline_ids.append(outline_id)
            text_id = self.canvas.create_text(
                x, y,
                text=word,
                font=("Arial", size, "bold"),
                fill="white",
                tags=f"word_{word_id}"
            )
            return [text_id], outline_ids

        # For now support up to 4 tones; map each char to a tone index
        tones = [ch for ch in tone_pair if ch in '12345']
        chars = list(word)
        count = len(chars)
        if len(tones) > 0:
            print(f"Aplicando cores por tom para '{word}' => tones={''.join(tones)}")

        # Use font metrics to compute exact per-character x positions keeping overall center
        canvas_font = tkfont.Font(family="Arial", size=size, weight="bold")
        total_width = canvas_font.measure(word)
        # If measurement fails, fallback to single text
        if total_width <= 0:
            outline_ids = []
            for dx in [-2, -1, 0, 1, 2]:
                for dy in [-2, -1, 0, 1, 2]:
                    if dx != 0 or dy != 0:
                        outline_id = self.canvas.create_text(
                            x + dx, y + dy,
                            text=word,
                            font=("Arial", size, "bold"),
                            fill="black",
                            tags=f"word_{word_id}_outline"
                        )
                        outline_ids.append(outline_id)
            text_id = self.canvas.create_text(
                x, y,
                text=word,
                font=("Arial", size, "bold"),
                fill="white",
                tags=f"word_{word_id}"
            )
            return [text_id], outline_ids

        left_edge = x - total_width / 2
        text_ids = []
        outline_ids = []
        for idx, ch in enumerate(chars):
            prefix = word[:idx]
            prefix_width = canvas_font.measure(prefix)
            char_width = canvas_font.measure(ch)
            char_center_x = left_edge + prefix_width + (char_width / 2)
            tone = tones[idx] if idx < len(tones) and tones[idx] in tone_to_color else None
            color = tone_to_color[tone] if tone else 'white'

            # Outline for each character
            for dx in [-2, -1, 0, 1, 2]:
                for dy in [-2, -1, 0, 1, 2]:
                    if dx != 0 or dy != 0:
                        outline_id = self.canvas.create_text(
                            int(char_center_x + dx), int(y + dy),
                            text=ch,
                            font=("Arial", size, "bold"),
                            fill="black",
                            tags=f"word_{word_id}_outline"
                        )
                        outline_ids.append(outline_id)

            # Main colored character
            text_id = self.canvas.create_text(
                int(char_center_x), y,
                text=ch,
                font=("Arial", size, "bold"),
                fill=color,
                tags=f"word_{word_id}"
            )
            text_ids.append(text_id)

        return text_ids, outline_ids
    
    def on_key_press(self, event):
        """Handle keyboard events for selected word"""
        # Handle Tab/Shift+Tab navigation regardless of current selection
        if event.keysym in ('Tab', 'ISO_Left_Tab'):
            # Shift detection: ISO_Left_Tab or Shift modifier with Tab
            is_shift = (event.keysym == 'ISO_Left_Tab') or bool(event.state & 0x1)
            self._select_next_word(forward=not is_shift)
            return "break"

        if self.selected_word_id is None:
            return
        
        word_id = self.selected_word_id
        # Defensive bounds check to avoid stale selection indices
        if not (0 <= int(word_id) < len(self.words_data)):
            self.clear_selection()
            return
        word_data = self.words_data[word_id]
        
        # Handle zoom in: +, =, Ctrl++, Ctrl+=
        if (event.keysym == 'plus' or 
            event.keysym == 'equal' or 
            (event.state & 0x4 and event.keysym == 'equal') or  # Ctrl+= 
            (event.state & 0x4 and event.keysym == 'plus') or   # Ctrl++
            event.char == '+'):
            # Increase word size
            self.change_word_size(word_id, 2)
        # Handle zoom out: -, Ctrl+-
        elif (event.keysym == 'minus' or 
              (event.state & 0x4 and event.keysym == 'minus') or  # Ctrl+-
              event.char == '-'):
            # Decrease word size
            self.change_word_size(word_id, -2)
        elif event.keysym.lower() == 'p':
            # Toggle pinyin display
            self.toggle_pinyin(word_id)
        elif event.keysym.lower() == 't':
            # Toggle translation display
            self.toggle_translation(word_id)
        elif event.keysym.lower() == 's':
            # Play word audio
            self.play_word_audio(word_id)
        elif event.keysym == 'Delete':
            # Delete word
            self.delete_word(word_id)

    def _select_next_word(self, forward: bool = True):
        """Select next/previous word for Tab navigation.
        forward=True selects the next word; forward=False selects the previous.
        """
        try:
            if not self.words_data or not self.word_objects:
                return
            # Ensure we only navigate through existing word ids
            available_ids = sorted([
                int(k) for k in self.word_objects.keys()
                if 0 <= int(k) < len(self.words_data)
            ])
            if not available_ids:
                return

            if (
                self.selected_word_id is None or
                int(self.selected_word_id) not in available_ids
            ):
                target_index = 0 if forward else len(available_ids) - 1
            else:
                current_index = available_ids.index(int(self.selected_word_id))
                delta = 1 if forward else -1
                target_index = (current_index + delta) % len(available_ids)

            self.select_word(available_ids[target_index])
        except Exception:
            # Be resilient to transient states during redraws/deletions
            pass
    
    def change_word_size(self, word_id: int, delta: int):
        """Change the size of a word"""
        word_data = self.words_data[word_id]
        new_size = max(8, min(120, word_data['size'] + delta))  # Limit between 8 and 120
        
        if new_size != word_data['size']:
            word_data['size'] = new_size
            self.redraw_word(word_id)
            self.save_positions()
    
    def toggle_pinyin(self, word_id: int):
        """Toggle pinyin display for a word"""
        word_data = self.words_data[word_id]
        word_data['hasPinyin'] = not word_data['hasPinyin']
        
        # Fetch pinyin from API if enabling
        if word_data['hasPinyin']:
            self.fetch_word_data(word_id)
        else:
            self.redraw_word(word_id)
            self.save_positions()
    
    def toggle_translation(self, word_id: int):
        """Toggle translation display for a word"""
        word_data = self.words_data[word_id]
        word_data['hasTranslation'] = not word_data['hasTranslation']
        
        # Fetch translation from API if enabling
        if word_data['hasTranslation']:
            self.fetch_word_data(word_id)
        else:
            self.redraw_word(word_id)
            self.save_positions()
    
    def delete_word(self, word_id: int):
        """Delete a word from the canvas and data"""
        # Remove from canvas
        if word_id not in self.word_objects or not (0 <= int(word_id) < len(self.words_data)):
            return
        word_obj = self.word_objects[word_id]
        self.canvas.delete(word_obj['text_id'])
        for outline_id in word_obj['outline_ids']:
            self.canvas.delete(outline_id)
        if word_obj['selection_rect_id']:
            self.canvas.delete(word_obj['selection_rect_id'])
        
        # Remove pinyin elements (primary and per-syllable)
        if word_obj.get('pinyin_text_id'):
            self.canvas.delete(word_obj['pinyin_text_id'])
        for tid in word_obj.get('pinyin_text_ids', []) or []:
            try:
                self.canvas.delete(tid)
            except Exception:
                pass
        for outline_id in word_obj.get('pinyin_outline_ids', []) or []:
            try:
                self.canvas.delete(outline_id)
            except Exception:
                pass
        
        # Remove translation elements
        if word_obj.get('translation_text_id'):
            self.canvas.delete(word_obj['translation_text_id'])
            for outline_id in word_obj.get('translation_outline_ids', []):
                self.canvas.delete(outline_id)
        
        # Remove from data by id, then rebuild drawing to maintain ids consistency
        try:
            del self.words_data[word_id]
        except Exception:
            return
        self.selected_word_id = None
        # Redraw everything to refresh ids and objects mapping
        self.draw_words()
        self.update_scroll_region()
        self.save_positions()
    
    def fetch_word_data(self, word_id: int):
        """Fetch pinyin and translation data - simplified version"""
        word_data = self.words_data[word_id]
        word = word_data['word']

        try:
            encoded = urllib.parse.quote(word, safe='')
            api_url = f"http://localhost:7998/word-api/{encoded}"
            response = requests.get(api_url, timeout=5)
            response.raise_for_status()

            # Try to parse JSON response
            try:
                data = response.json()
            except ValueError as json_err:
                print(f"word-api resposta não-JSON para: {word} — erro: {json_err}; tamanho corpo: {len(response.text)}")
                data = None

            # Print API response for debugging/inspection
            try:
                if data is not None:
                    print(f"word-api response for {word} (status {response.status_code}): {data}")
                else:
                    print(f"word-api response for {word} (status {response.status_code}): {response.text}")
            except Exception as log_err:
                print(f"Erro ao imprimir resposta da word-api para {word}: {log_err}")

            # Extract pinyin
            pinyin_value = None
            if isinstance(data, dict):
                if 'pinyin' in data:
                    pinyin_raw = data.get('pinyin')
                    if isinstance(pinyin_raw, list):
                        pinyin_value = ' '.join([str(x) for x in pinyin_raw if x])
                    elif pinyin_raw is not None:
                        pinyin_value = str(pinyin_raw).strip()
                elif 'pinyin_with_tone_marks' in data:
                    pinyin_value = str(data.get('pinyin_with_tone_marks') or '').strip()
                elif 'pinyin_tone_marks' in data:
                    pinyin_value = str(data.get('pinyin_tone_marks') or '').strip()

            # Extract translation
            translation_value = None
            if isinstance(data, dict):
                if 'translation' in data:
                    trans_raw = data.get('translation')
                elif 'translations' in data:
                    trans_raw = data.get('translations')
                elif 'english' in data:
                    trans_raw = data.get('english')
                elif 'meaning' in data:
                    trans_raw = data.get('meaning')
                else:
                    trans_raw = None

                if isinstance(trans_raw, list):
                    # Join unique, non-empty entries
                    unique = []
                    for item in trans_raw:
                        s = str(item).strip()
                        if s and s not in unique:
                            unique.append(s)
                    translation_value = '; '.join(unique)
                elif trans_raw is not None:
                    translation_value = str(trans_raw).strip()

            # Update local data if values were found; log when missing
            if pinyin_value:
                word_data['pinyin'] = pinyin_value
            else:
                print(f"word-api sem pinyin para: {word}")
            if translation_value:
                word_data['translation'] = translation_value
            else:
                print(f"word-api sem tradução para: {word}")

            # Extract and store tone pairs if provided
            tone_pair_value = None
            if isinstance(data, dict):
                tone_pair_raw = data.get('tone_pairs') or data.get('tone_pair') or data.get('tonePairs') or data.get('tonepair')
                if tone_pair_raw is not None:
                    tone_pair_value = str(tone_pair_raw).strip()
                    # Basic validation: keep only digits 1-5 and up to 4 chars
                    filtered = ''.join(ch for ch in tone_pair_value if ch in '12345')
                    if filtered:
                        tone_pair_value = filtered[:4]
                    else:
                        tone_pair_value = ''
            if tone_pair_value:
                word_data['tonePair'] = tone_pair_value

            # Redraw with potential new info and persist to CSV
            self.redraw_word(word_id)
            self.save_positions()

        except requests.exceptions.HTTPError as http_err:
            status = http_err.response.status_code if getattr(http_err, 'response', None) is not None else 'unknown'
            body_preview = ''
            try:
                body_preview = http_err.response.text[:200] if http_err.response is not None else ''
            except Exception:
                body_preview = ''
            print(f"HTTPError ao consultar word-api para: {word} — status: {status}; corpo: {body_preview}")
            self.redraw_word(word_id)
            self.save_positions()
        except requests.exceptions.Timeout:
            print(f"Timeout ao consultar word-api para: {word}")
            self.redraw_word(word_id)
            self.save_positions()
        except requests.exceptions.ConnectionError:
            print("Não foi possível conectar à word-api. Verifique se está em execução em http://localhost:7998")
            self.redraw_word(word_id)
            self.save_positions()
        except requests.exceptions.RequestException as e:
            print(f"Erro ao consultar word-api: {e}")
            self.redraw_word(word_id)
            self.save_positions()
    
    def redraw_word(self, word_id: int):
        """Redraw a word with updated properties"""
        word_data = self.words_data[word_id]
        word_obj = self.word_objects[word_id]
        
        # Delete old elements
        if word_obj.get('text_id'):
            self.canvas.delete(word_obj['text_id'])
        # Also delete any per-character text ids from previous draw
        for tid in word_obj.get('text_ids', []):
            try:
                self.canvas.delete(tid)
            except Exception:
                pass
        for outline_id in word_obj.get('outline_ids', []):
            self.canvas.delete(outline_id)
        if word_obj['selection_rect_id']:
            self.canvas.delete(word_obj['selection_rect_id'])
        
        # Delete pinyin elements if they exist (both primary and per-syllable)
        if word_obj.get('pinyin_text_id'):
            self.canvas.delete(word_obj['pinyin_text_id'])
        for tid in word_obj.get('pinyin_text_ids', []) or []:
            try:
                self.canvas.delete(tid)
            except Exception:
                pass
        for outline_id in word_obj.get('pinyin_outline_ids', []) or []:
            try:
                self.canvas.delete(outline_id)
            except Exception:
                pass
        word_obj['pinyin_text_id'] = None
        word_obj['pinyin_text_ids'] = []
        word_obj['pinyin_outline_ids'] = []
        
        # Delete translation elements if they exist
        if word_obj.get('translation_text_id'):
            self.canvas.delete(word_obj['translation_text_id'])
            for outline_id in word_obj.get('translation_outline_ids', []):
                self.canvas.delete(outline_id)
            word_obj['translation_text_id'] = None
            word_obj['translation_outline_ids'] = []
        
        # Get position
        x = word_data['position']['x']
        y = word_data['position']['y']
        word = word_data['word']
        size = word_data['size']
        
        # Create new text with tone coloring
        tone_pair = word_data.get('tonePair', '')
        if tone_pair:
            print(f"Redesenhando '{word}' com tone_pair={tone_pair}")
        text_ids, outline_ids = self.draw_word_with_tones(word_id, x, y, word, size, tone_pair)

        # Update word object
        word_obj['text_id'] = text_ids[0] if text_ids else None
        word_obj['text_ids'] = text_ids
        word_obj['outline_ids'] = outline_ids
        word_obj['selection_rect_id'] = None
        
        # Add pinyin if enabled and available
        if word_data.get('hasPinyin') and word_data.get('pinyin'):
            self.draw_pinyin_for_word(word_id, x, y - size - 5, word_data['pinyin'], int(size * 0.5))
        
        # Add translation if enabled and available
        if word_data.get('hasTranslation') and word_data.get('translation'):
            self.draw_translation_for_word(word_id, x, y + size + 10, word_data['translation'], int(size * 0.5))
        
        # Update scroll region
        self.update_scroll_region()
    
    def on_window_resize(self, event):
        """Handle window resize events"""
        if event.widget == self.root:
            # PanedWindow automatically handles resizing
            # Just update scroll region if needed
            self.root.after_idle(self.update_scroll_region)
    
    def play_word_audio(self, word_id: int):
        """Play audio for the selected word using gTTS"""
        if self.audio_loading:
            print("Audio already loading, please wait...")
            return
            
        word_data = self.words_data[word_id]
        word = word_data['word']
        
        # Check cache first
        if word in self.audio_cache:
            self._play_cached_audio(word)
            return
        
        # Generate and play audio in separate thread to avoid blocking UI
        self.audio_loading = True
        print(f"Generating audio for: {word}")
        
        thread = threading.Thread(target=self._generate_and_play_audio, args=(word,))
        thread.daemon = True
        thread.start()
    
    def _generate_and_play_audio(self, word: str):
        """Generate audio using gTTS and play it (runs in separate thread)"""
        try:
            # Generate speech using gTTS
            tts = gTTS(text=word, lang='zh', slow=False)
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(delete=False, suffix='.mp3') as temp_file:
                temp_filename = temp_file.name
                tts.save(temp_filename)
            
            # Cache the audio file path
            self.audio_cache[word] = temp_filename
            
            # Play the audio
            self._play_cached_audio(word)
            
        except Exception as e:
            print(f"Error generating audio: {e}")
        finally:
            self.audio_loading = False
    
    def _play_cached_audio(self, word: str):
        """Play cached audio file"""
        try:
            if word in self.audio_cache:
                audio_file = self.audio_cache[word]
                if os.path.exists(audio_file):
                    if self.audio_available:
                        # Use pygame mixer if available
                        pygame.mixer.music.load(audio_file)
                        pygame.mixer.music.play()
                        print(f"Playing audio for: {word}")
                    else:
                        # Fallback to system audio player
                        import subprocess
                        import platform
                        
                        system = platform.system()
                        if system == "Darwin":  # macOS
                            subprocess.run(["afplay", audio_file], check=False)
                        elif system == "Linux":
                            subprocess.run(["aplay", audio_file], check=False)
                        elif system == "Windows":
                            subprocess.run(["start", audio_file], shell=True, check=False)
                        
                        print(f"Playing audio for: {word} (using system player)")
                else:
                    # File doesn't exist, remove from cache
                    del self.audio_cache[word]
        except Exception as e:
            print(f"Error playing audio: {e}")

def main():
    """Main function to run the application"""
    root = tk.Tk()
    app = WordCanvasApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
