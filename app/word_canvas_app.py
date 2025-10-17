#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Word Canvas Application
Aplicação gráfica para carregar palavras do CSV e permitir drag and drop
"""

import tkinter as tk
from tkinter import ttk, messagebox
import csv
import os
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
        self.root.title("Word Canvas - Drag & Drop")
        self.root.geometry("1200x600")  # Increased width for side panel
        
        # Data storage
        self.words_data: List[Dict] = []
        self.word_objects: List[Dict] = {}
        self.selected_word_id: Optional[int] = None
        self.drag_data = {"x": 0, "y": 0, "item": None}
        
        # Audio system
        self.audio_cache = {}  # Cache for generated audio files
        self.audio_loading = False  # Flag to prevent multiple audio requests
        self.audio_available = False
        
        # Web panel state
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
        # Main frame with horizontal layout
        main_frame = ttk.Frame(self.root, padding="5")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights for responsive layout
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)  # Canvas takes 1/3 of space  
        main_frame.columnconfigure(1, weight=2)  # Web panel takes 2/3 of space
        main_frame.rowconfigure(0, weight=1)
        
        # Left side: Canvas with scrollbars
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
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
        
        # Right side: Web panel frame (initially hidden)
        self.web_frame = ttk.Frame(main_frame, relief="solid", borderwidth=1)
        # Don't grid it initially - will be shown when a word is clicked
        
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
            self.web_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
            self.web_panel_visible = True
        
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
        if character_data:
            # Character title
            text_widget.insert("end", f"{character}\n", "character")
            text_widget.insert("end", f"Frequência: {character_data.get('frequency', 'N/A')} | Consultas: {character_data.get('calls', 'N/A')}\n\n", "stats")
            
            # Decomposition (first, as requested)
            decomp = character_data.get('decomposition', 'N/A')
            decomp_meaning = character_data.get('decomposition_meaning', 'N/A')
            text_widget.insert("end", f"{decomp}\n", "decomp_title")
            text_widget.insert("end", f"{decomp_meaning}\n\n", "decomp_text")
            
            # Meaning
            meaning = character_data.get('meaning', 'N/A')
            text_widget.insert("end", f"{meaning}\n\n", "meaning")
            
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
        text_widget.tag_configure("related", font=("Arial", 11), foreground="#212529")
        text_widget.tag_configure("error", font=("Arial", 12, "bold"), foreground="#dc3545", justify="center")
        text_widget.tag_configure("info", font=("Arial", 10), foreground="#6c757d", justify="center")
        
        # Make text widget read-only
        text_widget.config(state="disabled")
        
        # Enable mouse wheel scrolling
        def _on_mousewheel(event):
            text_widget.yview_scroll(int(-1*(event.delta/120)), "units")
        
        text_widget.bind("<MouseWheel>", _on_mousewheel)
        text_widget.bind("<Button-4>", _on_mousewheel)
        text_widget.bind("<Button-5>", _on_mousewheel)
        
        # Separator frame for stroke order buttons
        button_frame = ttk.Frame(char_frame)
        button_frame.pack(fill="x", padx=10, pady=(5, 10))
        
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
            print(f"API response for {character}: {character_data}")
            
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
            self.web_frame.grid_remove()
            self.web_panel_visible = False
    
        
    def load_words_from_csv(self):
        """Load words from CSV file"""
        csv_path = os.path.join(os.path.dirname(__file__), "words.csv")
        
        try:
            self.words_data = []
            with open(csv_path, 'r', encoding='utf-8') as file:
                reader = csv.DictReader(file)
                for row in reader:
                    # Skip empty rows
                    if not row.get('word') or not row.get('word').strip():
                        continue
                        
                    # Convert float strings to int for positions
                    try:
                        position_x = int(float(row['position_x']))
                        position_y = int(float(row['position_y']))
                        size = int(float(row['size']))
                    except (ValueError, KeyError) as e:
                        print(f"Error parsing numeric values for word '{row.get('word', 'unknown')}': {e}")
                        continue
                    
                    word_data = {
                        'word': row['word'].strip(),
                        'size': size,
                        'position': {
                            'x': position_x,
                            'y': position_y
                        },
                        'hasPinyin': row.get('has_pinyin', 'false').lower() == 'true',
                        'hasTranslation': row.get('has_translation', 'false').lower() == 'true',
                        'pinyin': row.get('pinyin', '').strip(),
                        'translation': row.get('translation', '').strip()
                    }
                    self.words_data.append(word_data)
            
            print(f"Loaded {len(self.words_data)} words from CSV")
            
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
            
            # Create text object with thick black outline effect
            # Create outline by drawing text in black multiple times with slight offsets
            outline_ids = []
            for dx in [-2, -1, 0, 1, 2]:
                for dy in [-2, -1, 0, 1, 2]:
                    if dx != 0 or dy != 0:  # Skip center position
                        outline_id = self.canvas.create_text(
                            x + dx, y + dy,
                            text=word,
                            font=("Arial", size, "bold"),
                            fill="black",
                            tags=f"word_{i}_outline"
                        )
                        outline_ids.append(outline_id)
            
            # Create main text in white
            text_id = self.canvas.create_text(
                x, y,
                text=word,
                font=("Arial", size, "bold"),
                fill="white",
                tags=f"word_{i}"
            )
            
            # No background rectangle - just text with black outline
            
            # Store word object data
            self.word_objects[i] = {
                'text_id': text_id,
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
                self.draw_pinyin_for_word(i, x, y - size - 5, word_data['pinyin'], int(size * 0.6))
            
            # Add translation text if enabled
            if word_data.get('hasTranslation') and word_data.get('translation'):
                self.draw_translation_for_word(i, x, y + size + 10, word_data['translation'], int(size * 0.5))
        
        # Update scroll region to fit all content
        self.update_scroll_region()
    
    def draw_pinyin_for_word(self, word_id: int, x: int, y: int, pinyin: str, size: int):
        """Draw pinyin text above the main word"""
        # Create pinyin outline
        pinyin_outline_ids = []
        for dx in [-1, 0, 1]:
            for dy in [-1, 0, 1]:
                if dx != 0 or dy != 0:
                    outline_id = self.canvas.create_text(
                        x + dx, y + dy,
                        text=pinyin,
                        font=("Arial", size, "normal"),
                        fill="black",
                        tags=f"word_{word_id}_pinyin_outline"
                    )
                    pinyin_outline_ids.append(outline_id)
        
        # Create main pinyin text
        pinyin_text_id = self.canvas.create_text(
            x, y,
            text=pinyin,
            font=("Arial", size, "normal"),
            fill="lightblue",
            tags=f"word_{word_id}_pinyin"
        )
        
        # Store IDs
        self.word_objects[word_id]['pinyin_text_id'] = pinyin_text_id
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
            fill="lightgreen",
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
            word_items = [word_obj['text_id']] + word_obj['outline_ids']
            
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
        self.clear_selection()
        self.selected_word_id = word_id
        
        # Highlight selected word with selection box
        word_obj = self.word_objects[word_id]
        
        # Get bounding box of main word
        bbox = self.canvas.bbox(word_obj['text_id'])
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
        
        # Show web panel with word information
        word_data = self.words_data[word_id]
        self.show_web_panel(word_data)
    
    def clear_selection(self):
        """Clear word selection"""
        if self.selected_word_id is not None:
            word_obj = self.word_objects[self.selected_word_id]
            if word_obj['selection_rect_id']:
                self.canvas.delete(word_obj['selection_rect_id'])
                word_obj['selection_rect_id'] = None
            self.selected_word_id = None
    
    def save_positions(self):
        """Save current positions back to CSV"""
        csv_path = os.path.join(os.path.dirname(__file__), "words.csv")
        
        try:
            with open(csv_path, 'w', encoding='utf-8', newline='') as file:
                writer = csv.writer(file)
                writer.writerow(['word', 'size', 'position_x', 'position_y', 'has_pinyin', 'has_translation', 'pinyin', 'translation'])
                
                for word_data in self.words_data:
                    writer.writerow([
                        word_data['word'],
                        word_data['size'],
                        word_data['position']['x'],
                        word_data['position']['y'],
                        str(word_data['hasPinyin']).lower(),
                        str(word_data['hasTranslation']).lower(),
                        word_data.get('pinyin', ''),
                        word_data.get('translation', '')
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
    
    def on_key_press(self, event):
        """Handle keyboard events for selected word"""
        if self.selected_word_id is None:
            return
        
        word_id = self.selected_word_id
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
        word_obj = self.word_objects[word_id]
        self.canvas.delete(word_obj['text_id'])
        for outline_id in word_obj['outline_ids']:
            self.canvas.delete(outline_id)
        if word_obj['selection_rect_id']:
            self.canvas.delete(word_obj['selection_rect_id'])
        
        # Remove pinyin elements
        if word_obj.get('pinyin_text_id'):
            self.canvas.delete(word_obj['pinyin_text_id'])
            for outline_id in word_obj.get('pinyin_outline_ids', []):
                self.canvas.delete(outline_id)
        
        # Remove translation elements
        if word_obj.get('translation_text_id'):
            self.canvas.delete(word_obj['translation_text_id'])
            for outline_id in word_obj.get('translation_outline_ids', []):
                self.canvas.delete(outline_id)
        
        # Remove from data
        del self.words_data[word_id]
        del self.word_objects[word_id]
        
        # Clear selection
        self.selected_word_id = None
        
        # Update scroll region and save
        self.update_scroll_region()
        self.save_positions()
    
    def fetch_word_data(self, word_id: int):
        """Fetch pinyin and translation data - simplified version"""
        word_data = self.words_data[word_id]
        word = word_data['word']
        
        # Simplified version - just enable the flags without API call
        print(f"Pinyin/Translation enabled for: {word}")
        
        # For now, just redraw without fetching external data
        self.redraw_word(word_id)
        self.save_positions()
    
    def redraw_word(self, word_id: int):
        """Redraw a word with updated properties"""
        word_data = self.words_data[word_id]
        word_obj = self.word_objects[word_id]
        
        # Delete old elements
        self.canvas.delete(word_obj['text_id'])
        for outline_id in word_obj['outline_ids']:
            self.canvas.delete(outline_id)
        if word_obj['selection_rect_id']:
            self.canvas.delete(word_obj['selection_rect_id'])
        
        # Delete pinyin elements if they exist
        if word_obj.get('pinyin_text_id'):
            self.canvas.delete(word_obj['pinyin_text_id'])
            for outline_id in word_obj.get('pinyin_outline_ids', []):
                self.canvas.delete(outline_id)
            word_obj['pinyin_text_id'] = None
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
        
        # Create new text with outline
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
        
        # Create main text
        text_id = self.canvas.create_text(
            x, y,
            text=word,
            font=("Arial", size, "bold"),
            fill="white",
            tags=f"word_{word_id}"
        )
        
        # Update word object
        word_obj['text_id'] = text_id
        word_obj['outline_ids'] = outline_ids
        word_obj['selection_rect_id'] = None
        
        # Add pinyin if enabled and available
        if word_data.get('hasPinyin') and word_data.get('pinyin'):
            self.draw_pinyin_for_word(word_id, x, y - size - 5, word_data['pinyin'], int(size * 0.6))
        
        # Add translation if enabled and available
        if word_data.get('hasTranslation') and word_data.get('translation'):
            self.draw_translation_for_word(word_id, x, y + size + 10, word_data['translation'], int(size * 0.5))
        
        # Update scroll region
        self.update_scroll_region()
    
    def on_window_resize(self, event):
        """Handle window resize events"""
        if event.widget == self.root:
            # Update canvas size to match window
            self.root.after_idle(self.update_canvas_size)
    
    def update_canvas_size(self):
        """Update canvas size to fill available space"""
        # Get the current window size
        window_width = self.root.winfo_width()
        window_height = self.root.winfo_height()
        
        # Calculate available space for canvas (subtract scrollbar widths)
        canvas_width = max(400, window_width - 50)  # Minimum 400px width
        canvas_height = max(300, window_height - 100)  # Minimum 300px height
        
        # Configure canvas size
        self.canvas.configure(width=canvas_width, height=canvas_height)
    
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
