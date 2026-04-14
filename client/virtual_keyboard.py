"""
Virtual Keyboard for Gesture Control System
============================================
On-screen keyboard that can be controlled via hand gestures.
Supports multiple layouts, word prediction, and visual feedback.
"""

import tkinter as tk
from tkinter import font as tkfont
import threading
import time
from collections import deque
import pyautogui
from config import (
    KEYBOARD_WIDTH,
    KEYBOARD_HEIGHT,
    KEYBOARD_POSITION,
    KEY_HOVER_DELAY,
    KEY_PRESS_FEEDBACK,
    SHOW_KEY_PREVIEW,
    WORD_PREDICTION_ENABLED
)

try:
    from key_predictor import KeyPredictor
    from keyboard_layouts import (
        QWERTY_LAYOUT,
        NUMBERS_LAYOUT,
        SYMBOLS_LAYOUT,
        SPECIAL_KEYS
    )
except ImportError:
    # Fallback layouts if files don't exist yet
    QWERTY_LAYOUT = [
        ['`', '1', '2', '3', '4', '5', '6', '7', '8', '9', '0', '-', '=', 'BACKSPACE'],
        ['TAB', 'q', 'w', 'e', 'r', 't', 'y', 'u', 'i', 'o', 'p', '[', ']', '\\'],
        ['CAPS', 'a', 's', 'd', 'f', 'g', 'h', 'j', 'k', 'l', ';', "'", 'ENTER'],
        ['SHIFT', 'z', 'x', 'c', 'v', 'b', 'n', 'm', ',', '.', '/', 'SHIFT'],
        ['CTRL', 'WIN', 'ALT', 'SPACE', 'ALT', 'FN', 'CTRL']
    ]
    NUMBERS_LAYOUT = [
        ['7', '8', '9', '/'],
        ['4', '5', '6', '*'],
        ['1', '2', '3', '-'],
        ['0', '.', '=', '+']
    ]
    SYMBOLS_LAYOUT = [
        ['!', '@', '#', '$', '%', '^', '&', '*', '(', ')'],
        ['_', '+', '{', '}', '|', ':', '"', '<', '>', '?'],
        ['[', ']', '\\', ';', "'", ',', '.', '/', '~', '`']
    ]
    SPECIAL_KEYS = {
        'BACKSPACE': '\b',
        'ENTER': '\r',
        'TAB': '\t',
        'SPACE': ' ',
        'CAPS': 'CAPS',
        'SHIFT': 'SHIFT',
        'CTRL': 'CTRL',
        'ALT': 'ALT',
        'WIN': 'WIN',
        'FN': 'FN'
    }
    
    class KeyPredictor:
        def __init__(self):
            self.suggestions = []
        def predict(self, text):
            return []
        def add_word(self, word):
            pass
        def get_suggestions(self):
            return self.suggestions


class VirtualKeyboard:
    """Virtual keyboard with gesture control support"""
    
    def __init__(self, on_key_press=None, on_text_input=None):
        """
        Initialize virtual keyboard
        
        Args:
            on_key_press: Callback when key is pressed (receives key, key_type)
            on_text_input: Callback for text input (receives text)
        """
        self.root = None
        self.visible = False
        self.current_layout = 'qwerty'
        self.current_text = ""
        self.caps_lock = False
        self.shift_pressed = False
        self.current_hover_key = None
        self.hover_timer = None
        self.last_press_time = 0
        self.press_cooldown = 0.2  # seconds between key presses
        
        # Callbacks
        self.on_key_press = on_key_press
        self.on_text_input = on_text_input
        
        # Word predictor
        self.predictor = KeyPredictor() if WORD_PREDICTION_ENABLED else None
        
        # Keyboard windows and widgets
        self.key_widgets = {}
        self.key_frames = {}
        self.suggestion_buttons = []
        
        # Thread for keyboard UI
        self.ui_thread = None
        self.ui_running = False
        
        # Key press animation
        self.press_animation_queue = deque(maxlen=10)
        
        # Layout mappings
        self.layouts = {
            'qwerty': QWERTY_LAYOUT,
            'numbers': NUMBERS_LAYOUT,
            'symbols': SYMBOLS_LAYOUT
        }
        
        # Start keyboard thread
        self.start_keyboard_thread()
    
    def start_keyboard_thread(self):
        """Start keyboard UI in separate thread"""
        self.ui_running = True
        self.ui_thread = threading.Thread(target=self._run_keyboard_ui, daemon=True)
        self.ui_thread.start()
    
    def _run_keyboard_ui(self):
        """Run tkinter keyboard UI"""
        self.root = tk.Tk()
        self.root.title("Gesture Control Keyboard")
        self.root.overrideredirect(True)  # Remove window decorations
        self.root.attributes('-topmost', True)  # Keep on top
        self.root.configure(bg='#1a1a2e')
        
        # Set keyboard position
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        
        if KEYBOARD_POSITION == 'bottom':
            x = (screen_width - KEYBOARD_WIDTH) // 2
            y = screen_height - KEYBOARD_HEIGHT - 50
        elif KEYBOARD_POSITION == 'top':
            x = (screen_width - KEYBOARD_WIDTH) // 2
            y = 50
        else:  # floating
            x = (screen_width - KEYBOARD_WIDTH) // 2
            y = screen_height // 2 - KEYBOARD_HEIGHT // 2
        
        self.root.geometry(f"{KEYBOARD_WIDTH}x{KEYBOARD_HEIGHT}+{x}+{y}")
        
        # Create keyboard frame
        self.keyboard_frame = tk.Frame(self.root, bg='#1a1a2e')
        self.keyboard_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create text display area
        self.create_text_display()
        
        # Create suggestions bar
        if WORD_PREDICTION_ENABLED:
            self.create_suggestions_bar()
        
        # Create keyboard layout
        self.create_keyboard_layout()
        
        # Create layout switcher
        self.create_layout_switcher()
        
        # Hide initially
        self.root.withdraw()
        
        # Start animation updates
        self.update_animations()
        
        self.root.mainloop()
    
    def create_text_display(self):
        """Create text display area"""
        display_frame = tk.Frame(self.keyboard_frame, bg='#0f0f1a')
        display_frame.pack(fill=tk.X, padx=5, pady=5)
        
        self.text_display = tk.Text(
            display_frame,
            height=2,
            font=('Consolas', 14),
            bg='#0f0f1a',
            fg='#ffffff',
            insertbackground='#667eea',
            relief=tk.FLAT,
            wrap=tk.WORD
        )
        self.text_display.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Make display read-only
        self.text_display.config(state=tk.DISABLED)
    
    def create_suggestions_bar(self):
        """Create word prediction suggestions bar"""
        self.suggestions_frame = tk.Frame(self.keyboard_frame, bg='#1a1a2e')
        self.suggestions_frame.pack(fill=tk.X, padx=5, pady=5)
        
        # Will be populated dynamically
        self.update_suggestions()
    
    def create_keyboard_layout(self):
        """Create keyboard layout based on current selection"""
        # Clear existing keyboard
        for widget in self.keyboard_frame.winfo_children():
            if widget not in [self.text_display.master, self.suggestions_frame] \
               and widget != self.keyboard_frame.winfo_children()[0] if self.keyboard_frame.winfo_children() else True:
                widget.destroy()
        
        layout = self.layouts.get(self.current_layout, QWERTY_LAYOUT)
        
        for row_idx, row in enumerate(layout):
            row_frame = tk.Frame(self.keyboard_frame, bg='#1a1a2e')
            row_frame.pack(pady=2)
            
            for key in row:
                self.create_key_button(row_frame, key)
    
    def create_key_button(self, parent, key):
        """Create individual key button"""
        # Determine key width
        width = 6
        if key in ['BACKSPACE', 'ENTER', 'SHIFT', 'CAPS']:
            width = 8
        elif key == 'SPACE':
            width = 30
        elif key in ['TAB', 'CTRL', 'ALT', 'WIN', 'FN']:
            width = 5
        
        # Get display text
        display_text = self.get_key_display(key)
        
        # Create button
        btn = tk.Button(
            parent,
            text=display_text,
            width=width,
            height=1,
            font=('Arial', 10, 'bold'),
            bg='#2d2d3d',
            fg='#ffffff',
            activebackground='#667eea',
            activeforeground='#ffffff',
            relief=tk.RAISED,
            bd=1,
            cursor='hand2'
        )
        
        btn.pack(side=tk.LEFT, padx=2, pady=2)
        
        # Bind events
        btn.bind('<Enter>', lambda e, k=key: self.on_key_hover(k, btn))
        btn.bind('<Leave>', lambda e, k=key: self.on_key_leave(k, btn))
        btn.bind('<Button-1>', lambda e, k=key: self.on_key_click(k, btn))
        
        # Store reference
        self.key_widgets[key] = btn
        
        return btn
    
    def get_key_display(self, key):
        """Get display text for key"""
        if key in SPECIAL_KEYS:
            return key
        
        if self.caps_lock or self.shift_pressed:
            return key.upper()
        return key
    
    def create_layout_switcher(self):
        """Create layout switching buttons"""
        switcher_frame = tk.Frame(self.keyboard_frame, bg='#1a1a2e')
        switcher_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=5)
        
        layouts = [
            ('QWERTY', 'qwerty'),
            ('123', 'numbers'),
            ('#+=', 'symbols')
        ]
        
        for label, layout_name in layouts:
            btn = tk.Button(
                switcher_frame,
                text=label,
                width=8,
                font=('Arial', 8),
                bg='#3d3d4d',
                fg='#ffffff',
                command=lambda l=layout_name: self.switch_layout(l)
            )
            btn.pack(side=tk.LEFT, padx=5)
        
        # Close button
        close_btn = tk.Button(
            switcher_frame,
            text='✕',
            width=3,
            font=('Arial', 10, 'bold'),
            bg='#dc3545',
            fg='#ffffff',
            command=self.hide
        )
        close_btn.pack(side=tk.RIGHT, padx=5)
    
    def on_key_hover(self, key, button):
        """Handle key hover for gesture selection"""
        if self.current_hover_key == key:
            return
        
        self.current_hover_key = key
        
        # Cancel previous timer
        if self.hover_timer:
            self.hover_timer.cancel()
        
        # Start new timer for key press
        self.hover_timer = threading.Timer(KEY_HOVER_DELAY, lambda: self.on_key_click(key, button))
        self.hover_timer.start()
        
        # Visual feedback
        button.config(bg='#667eea')
    
    def on_key_leave(self, key, button):
        """Handle key leave"""
        if self.current_hover_key == key:
            self.current_hover_key = None
            
            # Cancel timer
            if self.hover_timer:
                self.hover_timer.cancel()
                self.hover_timer = None
            
            # Reset button color
            button.config(bg='#2d2d3d')
    
    def on_key_click(self, key, button):
        """Handle key click/press"""
        current_time = time.time()
        if current_time - self.last_press_time < self.press_cooldown:
            return
        
        self.last_press_time = current_time
        
        # Visual feedback
        if KEY_PRESS_FEEDBACK:
            self.animate_key_press(button)
        
        # Process key press
        self.process_key(key)
        
        # Reset hover
        if self.current_hover_key == key:
            self.current_hover_key = None
            if self.hover_timer:
                self.hover_timer.cancel()
                self.hover_timer = None
    
    def animate_key_press(self, button):
        """Animate key press"""
        original_bg = button.cget('bg')
        button.config(bg='#28a745')
        self.root.after(100, lambda: button.config(bg=original_bg))
    
    def process_key(self, key):
        """Process key press and update text"""
        if key in SPECIAL_KEYS:
            self.process_special_key(key)
        else:
            self.insert_character(key)
        
        # Call callback
        if self.on_key_press:
            self.on_key_press(key, 'special' if key in SPECIAL_KEYS else 'character')
    
    def process_special_key(self, key):
        """Process special keys (Enter, Backspace, etc.)"""
        if key == 'BACKSPACE':
            # Delete last character
            self.current_text = self.current_text[:-1]
            self.update_text_display()
            
            # Send backspace to system
            pyautogui.press('backspace')
            
        elif key == 'ENTER':
            # Add newline
            self.current_text += '\n'
            self.update_text_display()
            
            # Send enter to system
            pyautogui.press('enter')
            
        elif key == 'TAB':
            # Send tab
            pyautogui.press('tab')
            
        elif key == 'SPACE':
            self.insert_character(' ')
            
        elif key == 'CAPS':
            self.caps_lock = not self.caps_lock
            self.refresh_keyboard()
            
        elif key == 'SHIFT':
            self.shift_pressed = True
            self.refresh_keyboard()
            # Reset shift after next key
            self.root.after(500, self.reset_shift)
        
        # Update suggestions
        if WORD_PREDICTION_ENABLED:
            self.update_suggestions()
    
    def reset_shift(self):
        """Reset shift key state"""
        self.shift_pressed = False
        self.refresh_keyboard()
    
    def insert_character(self, char):
        """Insert character at cursor position"""
        if self.shift_pressed:
            char = char.upper()
            self.shift_pressed = False
        
        if self.caps_lock and char.isalpha():
            char = char.upper()
        
        self.current_text += char
        self.update_text_display()
        
        # Send to system (using pyautogui)
        pyautogui.write(char)
        
        # Call text input callback
        if self.on_text_input:
            self.on_text_input(char)
        
        # Update word predictions
        if WORD_PREDICTION_ENABLED:
            self.update_suggestions()
    
    def update_text_display(self):
        """Update the text display area"""
        self.text_display.config(state=tk.NORMAL)
        self.text_display.delete(1.0, tk.END)
        self.text_display.insert(1.0, self.current_text)
        self.text_display.config(state=tk.DISABLED)
        self.text_display.see(tk.END)
    
    def update_suggestions(self):
        """Update word prediction suggestions"""
        if not WORD_PREDICTION_ENABLED or not self.predictor:
            return
        
        # Clear existing suggestions
        for btn in self.suggestion_buttons:
            btn.destroy()
        self.suggestion_buttons.clear()
        
        # Get current word being typed
        words = self.current_text.split()
        current_word = words[-1] if words else ""
        
        # Get predictions
        suggestions = self.predictor.predict(current_word)
        
        # Create suggestion buttons
        for suggestion in suggestions[:5]:  # Max 5 suggestions
            btn = tk.Button(
                self.suggestions_frame,
                text=suggestion,
                font=('Arial', 10),
                bg='#667eea',
                fg='#ffffff',
                relief=tk.FLAT,
                cursor='hand2',
                command=lambda s=suggestion: self.insert_suggestion(s)
            )
            btn.pack(side=tk.LEFT, padx=5)
            self.suggestion_buttons.append(btn)
    
    def insert_suggestion(self, suggestion):
        """Insert word suggestion"""
        # Remove current word and insert suggestion
        words = self.current_text.split()
        if words:
            words[-1] = suggestion
            self.current_text = ' '.join(words)
        else:
            self.current_text = suggestion
        
        # Add space after suggestion
        self.current_text += ' '
        self.update_text_display()
        
        # Send to system
        pyautogui.write(suggestion + ' ')
        
        # Update predictions
        self.update_suggestions()
    
    def refresh_keyboard(self):
        """Refresh keyboard display (for caps/shift)"""
        for key, button in self.key_widgets.items():
            button.config(text=self.get_key_display(key))
    
    def switch_layout(self, layout_name):
        """Switch keyboard layout"""
        self.current_layout = layout_name
        self.create_keyboard_layout()
    
    def update_animations(self):
        """Update keyboard animations"""
        # Process animation queue
        while self.press_animation_queue:
            button = self.press_animation_queue.popleft()
            if button.winfo_exists():
                self.animate_key_press(button)
        
        # Schedule next update
        if self.ui_running and self.root:
            self.root.after(50, self.update_animations)
    
    def show(self):
        """Show keyboard"""
        if self.root:
            self.visible = True
            self.root.deiconify()
            self.root.lift()
            print("[KEYBOARD] Virtual keyboard shown")
    
    def hide(self):
        """Hide keyboard"""
        if self.root:
            self.visible = False
            self.root.withdraw()
            print("[KEYBOARD] Virtual keyboard hidden")
    
    def toggle(self):
        """Toggle keyboard visibility"""
        if self.visible:
            self.hide()
        else:
            self.show()
    
    def is_visible(self):
        """Check if keyboard is visible"""
        return self.visible
    
    def set_text(self, text):
        """Set keyboard text content"""
        self.current_text = text
        self.update_text_display()
    
    def get_text(self):
        """Get current text content"""
        return self.current_text
    
    def clear_text(self):
        """Clear all text"""
        self.current_text = ""
        self.update_text_display()
    
    def close(self):
        """Close keyboard and cleanup"""
        self.ui_running = False
        if self.root:
            self.root.quit()
            self.root.destroy()
        print("[KEYBOARD] Virtual keyboard closed")


# Standalone test function
def test_keyboard():
    """Test the virtual keyboard independently"""
    def on_key(key, key_type):
        print(f"[TEST] Key pressed: {key} (type: {key_type})")
    
    def on_text(text):
        print(f"[TEST] Text input: {text}")
    
    keyboard = VirtualKeyboard(on_key_press=on_key, on_text_input=on_text)
    
    print("Virtual keyboard test mode")
    print("Controls:")
    print("  - Hover over keys with mouse to simulate gesture")
    print("  - Click keys to type")
    print("  - Close window to exit")
    
    keyboard.show()
    
    try:
        keyboard.root.mainloop()
    except KeyboardInterrupt:
        keyboard.close()


if __name__ == "__main__":
    test_keyboard()