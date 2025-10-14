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

class WordCanvasApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Word Canvas - Drag & Drop")
        self.root.geometry("800x600")
        
        # Data storage
        self.words_data: List[Dict] = []
        self.word_objects: List[Dict] = {}
        self.selected_word_id: Optional[int] = None
        self.drag_data = {"x": 0, "y": 0, "item": None}
        
        # Create UI
        self.create_widgets()
        self.load_words_from_csv()
        self.draw_words()
        
    def create_widgets(self):
        """Create the main UI components"""
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure grid weights for responsive layout
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)
        
        # No control panel - removed all buttons and labels
        
        # Canvas with scrollbars
        canvas_frame = ttk.Frame(main_frame)
        canvas_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        canvas_frame.columnconfigure(0, weight=1)
        canvas_frame.rowconfigure(0, weight=1)
        
        # Canvas with light gray background and scrollable area
        self.canvas = tk.Canvas(canvas_frame, bg="#f0f0f0", 
                               scrollregion=(0, 0, 2000, 2000))  # Large scrollable area
        self.canvas.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Scrollbars
        v_scrollbar = ttk.Scrollbar(canvas_frame, orient=tk.VERTICAL, command=self.canvas.yview)
        v_scrollbar.grid(row=0, column=1, sticky=(tk.N, tk.S))
        self.canvas.configure(yscrollcommand=v_scrollbar.set)
        
        h_scrollbar = ttk.Scrollbar(main_frame, orient=tk.HORIZONTAL, command=self.canvas.xview)
        h_scrollbar.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E))
        self.canvas.configure(xscrollcommand=h_scrollbar.set)
        
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
                        'hasTranslation': row.get('has_translation', 'false').lower() == 'true'
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
                'selection_rect_id': None,  # Will be created when selected
                'data': word_data
            }
        
        # Update scroll region to fit all content
        self.update_scroll_region()
    
    def on_canvas_click(self, event):
        """Handle mouse click on canvas"""
        # Convert event coordinates to canvas coordinates (accounting for scroll)
        canvas_x = self.canvas.canvasx(event.x)
        canvas_y = self.canvas.canvasy(event.y)
        
        # Get clicked item using canvas coordinates
        item = self.canvas.find_closest(canvas_x, canvas_y)[0]
        
        # Find which word was clicked
        clicked_word_id = None
        for word_id, word_obj in self.word_objects.items():
            if (word_obj['text_id'] == item or 
                item in word_obj['outline_ids'] or 
                (word_obj['selection_rect_id'] and word_obj['selection_rect_id'] == item)):
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
        
        # Get text bounding box
        bbox = self.canvas.bbox(word_obj['text_id'])
        if bbox:
            # Create selection rectangle around the word
            selection_rect_id = self.canvas.create_rectangle(
                bbox[0] - 3, bbox[1] - 3,
                bbox[2] + 3, bbox[3] + 3,
                outline="blue",
                width=1,
                fill="",
                dash=(5, 5),  # Dashed line pattern
                tags=f"word_{word_id}_selection"
            )
            # Move rectangle behind text
            self.canvas.tag_lower(selection_rect_id, word_obj['text_id'])
            word_obj['selection_rect_id'] = selection_rect_id
        
        # No info label - removed
    
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
                writer.writerow(['word', 'size', 'position_x', 'position_y', 'has_pinyin', 'has_translation'])
                
                for word_data in self.words_data:
                    writer.writerow([
                        word_data['word'],
                        word_data['size'],
                        word_data['position']['x'],
                        word_data['position']['y'],
                        str(word_data['hasPinyin']).lower(),
                        str(word_data['hasTranslation']).lower()
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
        elif event.keysym == 'Delete':
            # Delete word
            self.delete_word(word_id)
    
    def change_word_size(self, word_id: int, delta: int):
        """Change the size of a word"""
        word_data = self.words_data[word_id]
        new_size = max(8, min(48, word_data['size'] + delta))  # Limit between 8 and 48
        
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

def main():
    """Main function to run the application"""
    root = tk.Tk()
    app = WordCanvasApp(root)
    root.mainloop()

if __name__ == "__main__":
    main()
