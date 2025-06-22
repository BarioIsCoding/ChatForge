import sys
import traceback
import os

try:
    import json
    import requests
    import re
    import markdown
    from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                                QHBoxLayout, QTextEdit, QPlainTextEdit, QLineEdit, QPushButton, 
                                QLabel, QComboBox, QScrollArea, QFrame, QToolButton,
                                QSizePolicy, QSpacerItem, QDialog, QMenu, QAction, QTreeWidget, 
                                QTreeWidgetItem, QTextBrowser, QCheckBox)
    from PyQt5.QtCore import (Qt, QThread, pyqtSignal, QSize, QPropertyAnimation, 
                            QRect, QPoint, QEasingCurve, QTimer)
    from PyQt5.QtGui import (QFont, QFontMetrics, QColor, QPalette, QIcon, QPixmap, 
                            QPainter, QPainterPath, QTextCursor, QFontDatabase)
    print("Successfully imported all required modules")
except ImportError as e:
    print(f"Error importing required module: {e}")
    print("Please make sure you have all required packages: pip install PyQt5 requests markdown")
    input("Press Enter to exit...")
    sys.exit(1)

# Constants for styling - exact hex colors from the screenshot
CHATGPT_BG = "#212121"  # Main background
CHATGPT_USER_MSG_BG = "#343541"  # User message background
CHATGPT_AI_MSG_BG = "#444654"  # AI message background
CHATGPT_INPUT_BG = "#303030"  # Input box background
CHATGPT_TEXT_COLOR = "#FFFFFF"  # Main text color
CHATGPT_SECONDARY_TEXT = "#BBBBBB"  # Secondary text color
CHATGPT_ACCENT = "#FFFFFF"  # Changed from green to white for send button
CHATGPT_PLACEHOLDER = "#8E8EA0"  # Placeholder text color
CHATGPT_BUTTON_BG = "#303030"  # Button background
CHATGPT_BORDER_COLOR = "#565869"  # Border color

# UI Constants
BORDER_RADIUS = "16px"  # Increased border radius for more rounded corners
FONT_FAMILY = "'Segoe UI', 'Open Sans', -apple-system, BlinkMacSystemFont, sans-serif"


class OllamaThread(QThread):
    """Thread for handling Ollama API requests without blocking the UI"""
    response_received = pyqtSignal(str)
    streaming_chunk_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, model, prompt, api_url, system_prompt="", use_streaming=False):
        super().__init__()
        self.model = model
        self.prompt = prompt
        self.api_url = api_url
        self.system_prompt = system_prompt
        self.use_streaming = use_streaming
        
    def process_system_prompt(self, model_display_name):
        """Process system prompt template variables"""
        if not self.system_prompt:
            return ""
        
        prompt = self.system_prompt
        
        # Extract model name and parameters
        model_info = format_model_name(self.model)
        formatted_name = model_info['formatted_name']
        param_count = extract_param_count(model_info['size_info'])
        
        # Replace template variables
        prompt = prompt.replace("%model%", formatted_name)
        prompt = prompt.replace("%parameters%", param_count)
        
        return prompt
        
    def run(self):
        try:
            print(f"OllamaThread: Starting API request to {self.api_url}")
            print(f"OllamaThread: Using model {self.model}")
            
            # Get model display name for template processing
            model_info = format_model_name(self.model)
            display_name = model_info['formatted_name']
            if model_info['size_info']:
                display_name += f" ({model_info['size_info']})"
            
            # Process system prompt templates
            processed_system_prompt = self.process_system_prompt(display_name)
            
            # Prepare the request payload
            payload = {
                "model": self.model,
                "prompt": self.prompt,
                "stream": self.use_streaming
            }
            
            # Add system prompt if provided
            if processed_system_prompt:
                print(f"OllamaThread: Using system prompt: {processed_system_prompt[:30]}...")
                payload["system"] = processed_system_prompt
            
            print(f"OllamaThread: Sending request with streaming={self.use_streaming}...")
            
            if self.use_streaming:
                # Handle streaming response
                full_response = ""
                
                response = requests.post(
                    f"{self.api_url}/api/generate",
                    json=payload,
                    stream=True,
                    timeout=60
                )
                
                if response.status_code == 200:
                    for line in response.iter_lines():
                        if line:
                            try:
                                chunk_data = json.loads(line)
                                if 'response' in chunk_data:
                                    chunk = chunk_data['response']
                                    full_response += chunk
                                    self.streaming_chunk_received.emit(chunk)
                            except json.JSONDecodeError:
                                print(f"Warning: Failed to parse JSON from line: {line}")
                    
                    # Send the complete response at the end
                    self.response_received.emit(full_response)
                else:
                    error_text = response.text
                    print(f"OllamaThread: Error response: {error_text}")
                    self.error_occurred.emit(f"Error: Status code {response.status_code} - {error_text}")
            else:
                # Handle non-streaming response
                response = requests.post(
                    f"{self.api_url}/api/generate",
                    json=payload,
                    timeout=60
                )
                
                print(f"OllamaThread: Response status code: {response.status_code}")
                
                if response.status_code == 200:
                    data = response.json()
                    self.response_received.emit(data.get('response', 'No response content'))
                else:
                    error_text = response.text
                    print(f"OllamaThread: Error response: {error_text}")
                    self.error_occurred.emit(f"Error: Status code {response.status_code} - {error_text}")
                    
        except requests.exceptions.RequestException as e:
            print(f"OllamaThread: Request exception: {str(e)}")
            self.error_occurred.emit(f"Network error: {str(e)}")
        except json.JSONDecodeError as e:
            print(f"OllamaThread: JSON decode error: {str(e)}")
            self.error_occurred.emit(f"Invalid response format: {str(e)}")
        except Exception as e:
            print(f"OllamaThread: Unexpected error: {str(e)}")
            import traceback
            traceback.print_exc()
            self.error_occurred.emit(f"Error: {str(e)}")

def extract_param_count(size_info):
    """Extract parameter count from size info (e.g., '7b' -> '7')"""
    if not size_info:
        return "unknown"
    
    # Remove 'b' or 'B' suffix
    if size_info.lower().endswith('b'):
        return size_info[:-1]
    
    return size_info

def format_model_name(name):
    """Format model name according to specified rules:
    - Remove everything before the last slash
    - Remove anything after colon (except size info)
    - Replace - and _ with space
    - Proper capitalization (e.g., Llama not llama)
    - Replace 'uncensored' with '(🗽)'
    - Extract size information (e.g., 7b, 13b) for display
    """
    # Store original name
    original_name = name
    
    # Remove everything before the last slash
    if '/' in name:
        name = name.split('/')[-1]
    
    # Extract size information after colon if it exists
    size_info = ""
    if ':' in name:
        parts = name.split(':', 1)
        name = parts[0]
        
        # Look for size patterns like 7b, 13b, 1.5b in the part after the colon
        size_match = re.search(r'(\d+(?:\.\d+)?[bB])', parts[1])
        if size_match:
            size_info = size_match.group(1)
    
    # Replace - and _ with space
    name = name.replace('-', ' ').replace('_', ' ')
    
    # Handle specific model families with proper capitalization
    model_families = {
        'llama': 'Llama',
        'mistral': 'Mistral',
        'codellama': 'CodeLlama',
        'wizardlm': 'WizardLM',
        'wizard': 'Wizard',
        'gemma': 'Gemma',
        'falcon': 'Falcon',
        'phi': 'Phi',
        'stablelm': 'StableLM',
        'tinyllama': 'TinyLlama',
        'vicuna': 'Vicuna',
        'nous': 'Nous',
        'orca': 'Orca',
        'yi': 'Yi',
    }
    
    # Apply model family capitalization
    for key, value in model_families.items():
        pattern = r'\b' + key + r'\b'  # Word boundary to match whole words
        name = re.sub(pattern, value, name, flags=re.IGNORECASE)
    
    # Replace 'uncensored' with '(🗽)'
    name = re.sub(r'\buncensored\b', '(🗽)', name, flags=re.IGNORECASE)
    
    # Capitalize first letter of each word for remaining terms
    words = name.split()
    capitalized_words = []
    for word in words:
        # Skip words that were already handled by model_families
        if word.lower() in [v.lower() for v in model_families.values()] or word == '(🗽)':
            capitalized_words.append(word)
        else:
            # Capitalize first letter of remaining words
            capitalized_words.append(word[0].upper() + word[1:] if word else '')
    
    formatted_name = ' '.join(capitalized_words)
    
    # Extract the base family name for grouping
    base_name = capitalized_words[0] if capitalized_words else ""
    
    return {
        'formatted_name': formatted_name,
        'size_info': size_info,
        'original_name': original_name,
        'base_family': base_name
    }


class ModelSelectionDialog(QDialog):
    """Dialog for selecting a model and configuring API settings"""
    def __init__(self, parent=None, api_url="http://localhost:11434"):
        super().__init__(parent)
        self.api_url = api_url
        self.selected_model = ""
        self.display_name = ""  # Store formatted display name
        
        self.setWindowTitle("Select Model")
        self.setFixedSize(500, 400)  # Made dialog larger to accommodate groups
        
        # Apply stylesheets
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {CHATGPT_BG};
                color: {CHATGPT_TEXT_COLOR};
                border-radius: {BORDER_RADIUS};
                font-family: {FONT_FAMILY};
            }}
            QLabel {{
                color: {CHATGPT_TEXT_COLOR};
                font-size: 14px;
                font-weight: 500;
            }}
            QComboBox {{
                background-color: {CHATGPT_INPUT_BG};
                color: {CHATGPT_TEXT_COLOR};
                border-radius: 12px;
                border: 1px solid #424242;
                padding: 8px 12px;
                min-height: 40px;
                font-size: 14px;
                font-family: {FONT_FAMILY};
            }}
            QLineEdit {{
                background-color: {CHATGPT_INPUT_BG};
                color: {CHATGPT_TEXT_COLOR};
                border-radius: 12px;
                border: 1px solid #424242;
                padding: 8px 12px;
                min-height: 40px;
                font-size: 14px;
                font-family: {FONT_FAMILY};
            }}
            QPushButton {{
                background-color: {CHATGPT_ACCENT};
                color: black;
                border: none;
                border-radius: 12px;
                padding: 10px 16px;
                font-weight: 600;
                font-size: 14px;
                font-family: {FONT_FAMILY};
            }}
            QPushButton:hover {{
                background-color: #E0E0E0;
            }}
            QListWidget {{
                background-color: {CHATGPT_INPUT_BG};
                color: {CHATGPT_TEXT_COLOR};
                border-radius: 12px;
                border: 1px solid #424242;
                padding: 8px;
                font-size: 14px;
                font-family: {FONT_FAMILY};
            }}
            QListWidget::item {{
                padding: 8px;
                border-radius: 6px;
            }}
            QListWidget::item:hover {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
            QListWidget::item:selected {{
                background-color: rgba(255, 255, 255, 0.2);
            }}
            QTreeWidget {{
                background-color: {CHATGPT_INPUT_BG};
                color: {CHATGPT_TEXT_COLOR};
                border-radius: 12px;
                border: 1px solid #424242;
                padding: 8px;
                font-size: 14px;
                font-family: {FONT_FAMILY};
            }}
            QTreeWidget::item {{
                padding: 6px;
            }}
            QTreeWidget::item:hover {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
            QTreeWidget::item:selected {{
                background-color: rgba(255, 255, 255, 0.2);
            }}
            QTreeWidget::branch {{
                background-color: transparent;
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Model selection
        model_label = QLabel("Select Model:")
        layout.addWidget(model_label)
        
        # Use TreeWidget for grouped model display
        self.model_tree = QTreeWidget()
        self.model_tree.setHeaderHidden(True)
        self.model_tree.setAnimated(True)
        self.model_tree.setIndentation(20)
        self.model_tree.setSelectionMode(QTreeWidget.SingleSelection)
        self.model_tree.itemClicked.connect(self.model_selected)
        layout.addWidget(self.model_tree)
        
        # API URL
        api_label = QLabel("API URL:")
        layout.addWidget(api_label)
        
        self.api_url_input = QLineEdit(self.api_url)
        layout.addWidget(self.api_url_input)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        refresh_btn = QPushButton("Refresh Models")
        refresh_btn.clicked.connect(self.fetch_models)
        button_layout.addWidget(refresh_btn)
        
        apply_btn = QPushButton("Apply")
        apply_btn.clicked.connect(self.apply_settings)
        button_layout.addWidget(apply_btn)
        
        layout.addLayout(button_layout)
        
        # Fetch models on init
        self.fetch_models()
    
    def model_selected(self, item, column):
        """Handle model selection from tree"""
        # Check if this is a model item (not a group)
        if hasattr(item, 'model_data'):
            self.selected_model = item.model_data['original_name']
            self.display_name = item.text(0)
    
    def fetch_models(self):
        """Fetch available models from Ollama API and organize them by family"""
        try:
            self.api_url = self.api_url_input.text().strip()
            self.model_tree.clear()
            
            # Add loading indicator
            loading_item = QTreeWidgetItem(self.model_tree)
            loading_item.setText(0, "Fetching models...")
            self.model_tree.addTopLevelItem(loading_item)
            
            response = requests.get(f"{self.api_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get('models', [])
                model_names = [model['name'] for model in models]
                
                # Clear the tree
                self.model_tree.clear()
                
                if model_names:
                    # Group models by family
                    model_families = {}
                    
                    for name in model_names:
                        model_info = format_model_name(name)
                        base_family = model_info['base_family']
                        
                        if base_family not in model_families:
                            model_families[base_family] = []
                        
                        model_families[base_family].append(model_info)
                    
                    # Add grouped models to tree
                    for family, models in sorted(model_families.items()):
                        # Create family group item
                        family_item = QTreeWidgetItem(self.model_tree)
                        family_item.setText(0, family)
                        family_item.setFlags(family_item.flags() | Qt.ItemIsAutoTristate)
                        family_item.setExpanded(True)  # Expand by default
                        
                        # Add models to this family
                        for model_info in sorted(models, key=lambda x: x['formatted_name']):
                            model_item = QTreeWidgetItem(family_item)
                            
                            # Format display with optional size info
                            display_text = model_info['formatted_name']
                            if model_info['size_info']:
                                # Add size info but without HTML formatting
                                display_text = f"{display_text} ({model_info['size_info']})"
                            
                            # Set plain text instead of HTML
                            model_item.setText(0, display_text)
                            
                            # Store original model data for later use
                            model_item.model_data = model_info
                else:
                    empty_item = QTreeWidgetItem(self.model_tree)
                    empty_item.setText(0, "No models found")
                    self.model_tree.addTopLevelItem(empty_item)
            else:
                self.model_tree.clear()
                error_item = QTreeWidgetItem(self.model_tree)
                error_item.setText(0, f"Error: Status code {response.status_code}")
                self.model_tree.addTopLevelItem(error_item)
        except Exception as e:
            self.model_tree.clear()
            error_item = QTreeWidgetItem(self.model_tree)
            error_item.setText(0, f"Error: {str(e)}")
            self.model_tree.addTopLevelItem(error_item)
    
    def apply_settings(self):
        """Apply the selected settings and close dialog"""
        self.api_url = self.api_url_input.text().strip()
        
        # Get selected item
        selected_items = self.model_tree.selectedItems()
        if selected_items and hasattr(selected_items[0], 'model_data'):
            model_data = selected_items[0].model_data
            self.selected_model = model_data['original_name']
            
            # Create display name - base model name with optional size
            display_name = model_data['formatted_name']
            if model_data['size_info']:
                self.display_name = f"{display_name} ({model_data['size_info']})"
            else:
                self.display_name = display_name
                
            self.accept()
        else:
            # No valid selection
            pass


class ChatBubble(QFrame):
    """Chat message bubble - redesigned with user messages on right, bot on left, more minimalist"""
    def __init__(self, message, is_user=False, parent=None):
        super().__init__(parent)
        self.is_user = is_user
        
        # Configure frame - no background
        self.setFrameShape(QFrame.NoFrame)
        self.setAutoFillBackground(False)
        
        # Create main layout with minimal margins
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 5, 0, 5)
        main_layout.setSpacing(0)
        
        # Create message container with proper alignment
        if is_user:
            main_layout.addStretch(1)  # Push content to the right
            
            # Create user message with right alignment and minimal container
            message_container = QWidget()
            user_layout = QVBoxLayout(message_container)
            user_layout.setContentsMargins(0, 0, 20, 0)
            user_layout.setSpacing(5)
            user_layout.setAlignment(Qt.AlignRight)
            
            # Use QLabel for user messages (simpler, no markdown)
            message_label = QLabel(message)
            message_label.setWordWrap(True)
            message_label.setTextFormat(Qt.PlainText)
            message_label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
            
            # Apply styling - right alignment
            message_label.setStyleSheet(f"""
                QLabel {{
                    background-color: transparent;
                    color: {CHATGPT_TEXT_COLOR};
                    font-family: {FONT_FAMILY};
                    font-size: 16px;
                    border: none;
                }}
            """)
            
            # Set alignment
            message_label.setAlignment(Qt.AlignRight | Qt.AlignTop)
            
            # Set maximum width to 80% of parent width (will adjust dynamically)
            message_label.setMaximumWidth(int(parent.width() * 0.8) if parent else 800)
            
            user_layout.addWidget(message_label)
            main_layout.addWidget(message_container)
            
        else:
            # Bot message on left
            message_container = QWidget()
            bot_layout = QVBoxLayout(message_container)
            bot_layout.setContentsMargins(20, 0, 0, 0)
            bot_layout.setSpacing(5)
            bot_layout.setAlignment(Qt.AlignLeft)
            
            # Use QTextEdit for bot messages (supports markdown, no scrollbars)
            message_view = QTextEdit()
            message_view.setReadOnly(True)
            message_view.setFrameStyle(QFrame.NoFrame)
            message_view.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            message_view.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
            
            # Apply styling - left alignment
            message_view.setStyleSheet(f"""
                QTextEdit {{
                    background-color: transparent;
                    color: {CHATGPT_TEXT_COLOR};
                    font-family: {FONT_FAMILY};
                    font-size: 16px;
                    border: none;
                    selection-color: white;
                    selection-background-color: #3390FF;
                }}
            """)
            
            # Set maximum width to 80% of parent width (will adjust dynamically)
            message_view.setMaximumWidth(int(parent.width() * 0.8) if parent else 800)
            
            # Convert markdown to HTML
            try:
                # Define custom CSS for markdown
                markdown_css = """
                <style>
                    body {
                        font-family: 'Segoe UI', sans-serif;
                        font-size: 16px;
                        line-height: 1.6;
                        color: #FFFFFF;
                    }
                    pre {
                        background-color: #2D2D2D;
                        border-radius: 5px;
                        padding: 10px;
                        overflow-x: auto;
                    }
                    code {
                        font-family: 'Consolas', monospace;
                        background-color: #2D2D2D;
                        padding: 2px 4px;
                        border-radius: 3px;
                    }
                    table {
                        border-collapse: collapse;
                        width: 100%;
                        margin: 10px 0;
                    }
                    th, td {
                        border: 1px solid #444;
                        padding: 8px;
                        text-align: left;
                    }
                    th {
                        background-color: #333;
                    }
                    a {
                        color: #3390FF;
                        text-decoration: none;
                    }
                    a:hover {
                        text-decoration: underline;
                    }
                    blockquote {
                        border-left: 4px solid #444;
                        margin-left: 0;
                        padding-left: 15px;
                        color: #BBB;
                    }
                    img {
                        max-width: 100%;
                        height: auto;
                    }
                    h1, h2, h3, h4, h5, h6 {
                        margin-top: 20px;
                        margin-bottom: 10px;
                        font-weight: 600;
                    }
                    ol, ul {
                        padding-left: 20px;
                    }
                </style>
                """
                
                # Preserve newlines before markdown conversion
                processed_message = message.replace('\n', '  \n')
                
                # Convert markdown to HTML
                html_content = markdown.markdown(
                    processed_message,
                    extensions=['tables', 'fenced_code', 'codehilite']
                )
                
                # Set the HTML content with our custom CSS
                message_view.setHtml(markdown_css + html_content)
            except Exception as e:
                # Fallback to plain text if markdown conversion fails
                message_view.setPlainText(message)
                print(f"Markdown conversion error: {str(e)}")
            
            # Auto-adjust height based on content
            message_view.document().adjustSize()
            # Convert float to int for setFixedHeight
            doc_height = int(message_view.document().size().height() + 10)
            message_view.setFixedHeight(doc_height)
            
            bot_layout.addWidget(message_view)
            
            # Add buttons row (copy, thumbs up/down) for assistant messages only
            buttons_layout = QHBoxLayout()
            buttons_layout.setContentsMargins(0, 0, 0, 0)
            buttons_layout.setSpacing(10)
            buttons_layout.setAlignment(Qt.AlignLeft)
            
            # Add copy button
            copy_btn = QToolButton()
            copy_btn.setToolTip("Copy to clipboard")
            copy_btn.setStyleSheet(f"""
                QToolButton {{
                    background-color: transparent;
                    border: none;
                    color: {CHATGPT_SECONDARY_TEXT};
                    padding: 0px;
                    font-size: 14px;
                }}
                QToolButton:hover {{
                    background-color: rgba(255, 255, 255, 0.1);
                    border-radius: 4px;
                }}
            """)
            copy_btn.setText("📋")
            copy_btn.clicked.connect(lambda: QApplication.clipboard().setText(message))
            
            # Add Thumbs up and down buttons
            thumbs_up = QToolButton()
            thumbs_up.setToolTip("Thumbs up")
            thumbs_up.setText("👍")
            thumbs_up.setStyleSheet(copy_btn.styleSheet())
            
            thumbs_down = QToolButton()
            thumbs_down.setToolTip("Thumbs down")
            thumbs_down.setText("👎")
            thumbs_down.setStyleSheet(copy_btn.styleSheet())
            
            buttons_layout.addWidget(copy_btn)
            buttons_layout.addWidget(thumbs_up)
            buttons_layout.addWidget(thumbs_down)
            buttons_layout.addStretch()
            
            bot_layout.addLayout(buttons_layout)
            
            main_layout.addWidget(message_container)
            main_layout.addStretch(1)  # Push content to the left
    
    def resizeEvent(self, event):
        """Handle resize events to adjust text width"""
        super().resizeEvent(event)
        
        # Find child widgets to adjust
        for child in self.findChildren(QWidget):
            if isinstance(child, QLabel) or isinstance(child, QTextEdit):
                # Adjust width to 80% of the parent width
                child.setMaximumWidth(int(self.width() * 0.8))


class SystemPromptDialog(QDialog):
    """Dialog for configuring system prompt"""
    def __init__(self, parent=None, current_prompt="", use_streaming=False):
        super().__init__(parent)
        self.system_prompt = current_prompt
        self.use_streaming = use_streaming
        
        self.setWindowTitle("Configure System Prompt")
        self.setMinimumSize(600, 450)
        
        # Apply stylesheets
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {CHATGPT_BG};
                color: {CHATGPT_TEXT_COLOR};
                border-radius: {BORDER_RADIUS};
                font-family: {FONT_FAMILY};
            }}
            QLabel {{
                color: {CHATGPT_TEXT_COLOR};
                font-size: 14px;
                font-weight: 500;
            }}
            QTextEdit {{
                background-color: {CHATGPT_INPUT_BG};
                color: {CHATGPT_TEXT_COLOR};
                border-radius: 12px;
                border: 1px solid #424242;
                padding: 8px 12px;
                font-size: 14px;
                font-family: {FONT_FAMILY};
            }}
            QPushButton {{
                background-color: {CHATGPT_ACCENT};
                color: black;
                border: none;
                border-radius: 12px;
                padding: 10px 16px;
                font-weight: 600;
                font-size: 14px;
                font-family: {FONT_FAMILY};
            }}
            QPushButton:hover {{
                background-color: #E0E0E0;
            }}
            QCheckBox {{
                color: {CHATGPT_TEXT_COLOR};
                font-size: 14px;
            }}
            QCheckBox::indicator {{
                width: 18px;
                height: 18px;
                border: 2px solid {CHATGPT_SECONDARY_TEXT};
                border-radius: 3px;
            }}
            QCheckBox::indicator:checked {{
                background-color: {CHATGPT_ACCENT};
                border: 2px solid {CHATGPT_ACCENT};
            }}
        """)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(16)
        layout.setContentsMargins(24, 24, 24, 24)
        
        # Explanation label
        explanation = QLabel(
            "The system prompt is sent to the model with every message. "
            "Use it to give the model instructions on how to behave or provide context."
        )
        explanation.setWordWrap(True)
        layout.addWidget(explanation)
        
        # Template explanation
        template_explanation = QLabel(
            "You can use templates in your prompt:\n"
            "%model% - Will be replaced with the model name\n"
            "%parameters% - Will be replaced with parameter count (without 'b')"
        )
        template_explanation.setWordWrap(True)
        layout.addWidget(template_explanation)
        
        # System prompt input
        self.prompt_input = QTextEdit(self)
        self.prompt_input.setPlaceholderText("Enter system prompt here...")
        self.prompt_input.setText(current_prompt)
        layout.addWidget(self.prompt_input, 1)
        
        # Streaming option
        self.streaming_checkbox = QCheckBox("Enable streaming responses")
        self.streaming_checkbox.setChecked(use_streaming)
        layout.addWidget(self.streaming_checkbox)
        
        # Examples label
        examples_label = QLabel("Examples:")
        layout.addWidget(examples_label)
        
        # Example prompts
        examples = [
            "You are a helpful, creative, and friendly assistant.",
            "You are an expert programmer. Provide concise and efficient code examples.",
            "You are %model%, an AI assistant with %parameters% billion parameters. Help with clear and concise answers."
        ]
        
        examples_layout = QVBoxLayout()
        for example in examples:
            example_btn = QPushButton(example)
            example_btn.clicked.connect(lambda checked, text=example: self.set_example(text))
            examples_layout.addWidget(example_btn)
        
        layout.addLayout(examples_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.addStretch()
        
        clear_btn = QPushButton("Clear")
        clear_btn.clicked.connect(self.clear_prompt)
        button_layout.addWidget(clear_btn)
        
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.save_prompt)
        button_layout.addWidget(save_btn)
        
        layout.addLayout(button_layout)
    
    def set_example(self, text):
        """Set an example prompt"""
        self.prompt_input.setText(text)
    
    def clear_prompt(self):
        """Clear the prompt input"""
        self.prompt_input.clear()
    
    def save_prompt(self):
        """Save the prompt and close dialog"""
        self.system_prompt = self.prompt_input.toPlainText().strip()
        self.use_streaming = self.streaming_checkbox.isChecked()
        
        # Save configuration to file
        try:
            config = {
                'system_prompt': self.system_prompt,
                'use_streaming': self.use_streaming
            }
            
            with open('ollama_config.json', 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Error saving configuration: {str(e)}")
        
        self.accept()


class CommandPredictionPopup(QFrame):
    """Popup widget showing command predictions"""
    
    command_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Configure frame
        self.setFrameShape(QFrame.StyledPanel)
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {CHATGPT_INPUT_BG};
                border: 1px solid #424242;
                border-radius: 8px;
            }}
            QLabel {{
                color: {CHATGPT_TEXT_COLOR};
                font-size: 14px;
                padding: 4px 8px;
            }}
            QLabel:hover {{
                background-color: rgba(255, 255, 255, 0.1);
                border-radius: 4px;
            }}
        """)
        
        # Layout
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(8, 8, 8, 8)
        self.layout.setSpacing(2)
        
        self.prediction_widgets = []
    
    def update_predictions(self, predictions):
        """Update the prediction list"""
        # Clear existing predictions
        for widget in self.prediction_widgets:
            self.layout.removeWidget(widget)
            widget.deleteLater()
        self.prediction_widgets = []
        
        if not predictions:
            self.hide()
            return
        
        # Add new predictions
        for pred in predictions:
            # Create a label without HTML and use stylesheet for bold text
            cmd_widget = QLabel(f"{pred['command']} - {pred['description']}")
            cmd_widget.setStyleSheet("font-weight: bold;")
            cmd_widget.setCursor(Qt.PointingHandCursor)
            cmd_widget.setTextFormat(Qt.PlainText)  # Use plain text instead of rich text
            cmd_widget.mousePressEvent = lambda e, cmd=pred['command']: self.select_command(cmd)
            
            self.layout.addWidget(cmd_widget)
            self.prediction_widgets.append(cmd_widget)
        
        # Show the popup
        self.adjustSize()
        self.show()
    
    def select_command(self, command):
        """Emit signal when a command is selected"""
        self.command_selected.emit(command)
        self.hide()


class SlashCommandHandler:
    """Handles slash command processing and prediction"""
    
    def __init__(self, chat_gui):
        self.chat_gui = chat_gui
        self.commands = {
            "/clear": {
                "description": "Clear the chat history",
                "action": self.clear_chat
            },
            "/models": {
                "description": "Open model selection panel",
                "action": self.open_models
            },
            "/system": {
                "description": "Configure system prompt",
                "action": self.open_system_prompt
            },
            "/bye": {
                "description": "Exit the application",
                "action": self.exit_app
            }
        }
    
    def get_predictions(self, current_text):
        """Get command predictions based on current text"""
        if not current_text.startswith('/'):
            return []
        
        predictions = []
        for cmd in self.commands.keys():
            if cmd.startswith(current_text):
                predictions.append({
                    "command": cmd,
                    "description": self.commands[cmd]["description"]
                })
        
        return predictions
    
    def process_command(self, command_text):
        """Process a slash command"""
        command = command_text.split()[0]  # Get the first word as the command
        
        if command in self.commands:
            # Execute the command action
            self.commands[command]["action"]()
            return True
        
        return False
    
    # Command actions
    def clear_chat(self):
        """Clear the chat history"""
        self.chat_gui.conversation_history = []
        self.chat_gui.setup_welcome_view()
        # If we have an input layout, center it for the welcome screen
        if hasattr(self.chat_gui, 'input_layout'):
            self.chat_gui.input_layout.setContentsMargins(120, 10, 120, 24)
    
    def open_models(self):
        """Open the model selection dialog"""
        self.chat_gui.show_model_dialog()
    
    def open_system_prompt(self):
        """Open the system prompt dialog"""
        self.chat_gui.show_system_prompt_dialog()
    
    def exit_app(self):
        """Exit the application"""
        self.chat_gui.close()


class OllamaChatGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Ollama Chat")
        self.setGeometry(100, 100, 1200, 800)
        self.conversation_history = []
        self.api_url = "http://localhost:11434"
        self.current_model = ""
        self.system_prompt = ""
        self.use_streaming = False
        self.current_streaming_bubble = None
        
        # Load configuration
        self.load_config()
        
        # Set up slash command handler
        self.command_handler = SlashCommandHandler(self)
        
        # Set up custom fonts with improved rendering
        self.setup_fonts()
        
        # Setup UI
        self.setup_ui()
        
        # Set up initial model
        QTimer.singleShot(500, self.show_model_dialog)
    
    def load_config(self):
        """Load configuration from file"""
        try:
            if os.path.exists('ollama_config.json'):
                with open('ollama_config.json', 'r') as f:
                    config = json.load(f)
                    
                    if 'system_prompt' in config:
                        self.system_prompt = config['system_prompt']
                    
                    if 'use_streaming' in config:
                        self.use_streaming = config['use_streaming']
                        
                print(f"Loaded configuration. System prompt: {len(self.system_prompt)} chars, Streaming: {self.use_streaming}")
        except Exception as e:
            print(f"Error loading configuration: {str(e)}")
        
    def setup_fonts(self):
        """Set up high-quality fonts for the application with improved rendering"""
        # Load fonts from system and set default with improved settings
        font = QFont("Segoe UI", 14)
        font.setStyleHint(QFont.SansSerif)
        font.setHintingPreference(QFont.PreferFullHinting)
        font.setWeight(QFont.Medium)
        # Enable subpixel antialiasing for better text rendering
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
        QApplication.setFont(font)
        
    def setup_ui(self):
        # Apply global stylesheet
        self.setStyleSheet(f"""
            QMainWindow, QWidget {{
                background-color: {CHATGPT_BG};
                color: {CHATGPT_TEXT_COLOR};
                font-family: {FONT_FAMILY};
            }}
            
            QScrollArea {{
                border: none;
                background-color: {CHATGPT_BG};
            }}
            
            QScrollBar:vertical {{
                background-color: {CHATGPT_BG};
                width: 8px;
                margin: 0px;
            }}
            
            QScrollBar::handle:vertical {{
                background-color: #555555;
                min-height: 30px;
                border-radius: 4px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background-color: #777777;
            }}
            
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0px;
            }}
        """)
        
        # Main layout with central widget
        central_widget = QWidget()
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        # Header
        header_widget = QWidget()
        header_widget.setFixedHeight(48)
        header_widget.setStyleSheet(f"background-color: {CHATGPT_BG};")
        
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(15, 0, 15, 0)
        
        # High-quality logo/chat name rendering - clickable to select model
        self.header_title = QLabel("Ollama Chat")
        self.header_title.setStyleSheet(f"""
            font-weight: 600; 
            font-size: 18px;
            color: {CHATGPT_TEXT_COLOR};
            font-family: {FONT_FAMILY};
            padding: 8px 14px;
        """)
        self.header_title.setCursor(Qt.PointingHandCursor)  # Change cursor to indicate clickable
        self.header_title.mousePressEvent = self.title_clicked  # Set click handler
        
        header_layout.addWidget(self.header_title)
        header_layout.addStretch()
        
        # Add system prompt button to the top right
        self.system_prompt_btn = QToolButton()
        self.system_prompt_btn.setText("⚙️")
        self.system_prompt_btn.setToolTip("Configure System Prompt")
        self.system_prompt_btn.setStyleSheet(f"""
            QToolButton {{
                background-color: transparent;
                border-radius: 8px;
                padding: 6px;
                color: {CHATGPT_SECONDARY_TEXT};
                font-size: 16px;
            }}
            QToolButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
        """)
        self.system_prompt_btn.clicked.connect(self.show_system_prompt_dialog)
        header_layout.addWidget(self.system_prompt_btn)
        
        main_layout.addWidget(header_widget)
        
        # Chat area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.scroll_area.setFrameShape(QFrame.NoFrame)
        
        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setContentsMargins(0, 0, 0, 0)
        self.chat_layout.setAlignment(Qt.AlignTop)
        self.chat_layout.setSpacing(0)
        
        # Add welcome message/view
        self.setup_welcome_view()
        
        self.scroll_area.setWidget(self.chat_widget)
        main_layout.addWidget(self.scroll_area, 1)  # Give chat area more space
        
        # Input area at the bottom (ChatGPT style)
        self.input_container = QWidget()
        self.input_container.setStyleSheet(f"background-color: {CHATGPT_BG};")
        self.input_layout = QVBoxLayout(self.input_container)
        
        # Store original margins to restore them when chat has messages
        self.original_input_margins = (16, 10, 16, 24)
        
        # If chat is empty, use larger margins and center the input
        if len(self.conversation_history) == 0:
            self.input_layout.setContentsMargins(120, 10, 120, 24)
        else:
            self.input_layout.setContentsMargins(*self.original_input_margins)
        
        # Input box with buttons
        self.input_frame = QFrame()
        self.input_frame.setStyleSheet(f"""
            QFrame {{
                background-color: {CHATGPT_INPUT_BG};
                border-radius: {BORDER_RADIUS};
                border: 1px solid #424242;
            }}
        """)
        
        input_box_layout = QVBoxLayout(self.input_frame)
        input_box_layout.setContentsMargins(16, 12, 16, 12)
        input_box_layout.setSpacing(8)
        
        # Message input
        self.message_input = QTextEdit()
        self.message_input.setPlaceholderText("Ask anything or type / for commands")
        self.message_input.setAcceptRichText(False)
        self.message_input.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.message_input.setStyleSheet(f"""
            QTextEdit {{
                background-color: transparent;
                border: none;
                color: {CHATGPT_TEXT_COLOR};
                font-size: 16px;
                padding: 0px;
                font-family: {FONT_FAMILY};
            }}
            QTextEdit:focus {{
                outline: none;
            }}
        """)
        self.message_input.setFixedHeight(60)
        
        # Command prediction popup
        self.prediction_popup = CommandPredictionPopup(self)
        self.prediction_popup.command_selected.connect(self.insert_command)
        self.prediction_popup.hide()
        
        # Button row below the input
        button_row = QWidget()
        button_row.setStyleSheet("background-color: transparent;")
        button_row_layout = QHBoxLayout(button_row)
        button_row_layout.setContentsMargins(0, 0, 0, 0)
        button_row_layout.setSpacing(10)
        
        # Action buttons like in ChatGPT
        button_style = f"""
            QToolButton {{
                background-color: transparent;
                border-radius: 8px;
                padding: 6px;
                color: {CHATGPT_SECONDARY_TEXT};
                font-size: 14px;
            }}
            QToolButton:hover {{
                background-color: rgba(255, 255, 255, 0.1);
            }}
        """
        
        # "+" button 
        plus_btn = QToolButton()
        plus_btn.setText("+")
        plus_btn.setObjectName("plus_button")
        plus_btn.setToolTip("New chat")
        plus_btn.setStyleSheet(button_style)
        plus_btn.clicked.connect(lambda: self.command_handler.clear_chat())
        
        # Search button
        search_btn = QToolButton()
        search_btn.setText("🔍")
        search_btn.setObjectName("search_button")
        search_btn.setToolTip("Search models")
        search_btn.setStyleSheet(button_style)
        search_btn.clicked.connect(self.show_model_dialog)
        
        # Send button (right side) - now white with black text
        self.send_btn = QToolButton()
        self.send_btn.setText("▶")
        self.send_btn.setObjectName("send_button")  
        self.send_btn.setToolTip("Send message")
        self.send_btn.setStyleSheet(f"""
            QToolButton {{
                background-color: {CHATGPT_ACCENT};
                border-radius: 12px;
                padding: 8px;
                color: #000000;
                font-weight: bold;
            }}
            QToolButton:hover {{
                background-color: #E0E0E0;
            }}
        """)
        self.send_btn.clicked.connect(self.send_message)
        
        button_row_layout.addWidget(plus_btn)
        button_row_layout.addWidget(search_btn)
        button_row_layout.addStretch()
        button_row_layout.addWidget(self.send_btn)
        
        input_box_layout.addWidget(self.message_input)
        input_box_layout.addWidget(button_row)
        
        self.input_layout.addWidget(self.input_frame)
        
        # Add disclaimer at bottom (like ChatGPT's "ChatGPT can make mistakes" text)
        disclaimer = QLabel("Ollama can make mistakes. Check important info.")
        disclaimer.setStyleSheet(f"color: {CHATGPT_PLACEHOLDER}; font-size: 12px; text-align: center; font-family: {FONT_FAMILY};")
        disclaimer.setAlignment(Qt.AlignCenter)
        self.input_layout.addWidget(disclaimer)
        
        main_layout.addWidget(self.input_container)
        
        self.setCentralWidget(central_widget)
        
        # Set up key press event for message input
        self.message_input.installEventFilter(self)
        self.message_input.textChanged.connect(self.on_text_changed)
    
    def insert_command(self, command):
        """Insert selected command into input field"""
        self.message_input.setText(command + " ")
        self.message_input.setFocus()
        # Move cursor to end
        cursor = self.message_input.textCursor()
        cursor.movePosition(QTextCursor.End)
        self.message_input.setTextCursor(cursor)
    
    def on_text_changed(self):
        """Handle text changes in the input field for command prediction"""
        current_text = self.message_input.toPlainText()
        
        # Check if we need to show command predictions
        if current_text.startswith('/'):
            # Get command predictions
            predictions = self.command_handler.get_predictions(current_text)
            
            if predictions:
                # Position popup below input box
                popup_pos = self.message_input.mapToGlobal(
                    self.message_input.rect().bottomLeft()
                )
                self.prediction_popup.move(popup_pos)
                self.prediction_popup.update_predictions(predictions)
            else:
                self.prediction_popup.hide()
        else:
            self.prediction_popup.hide()
    
    def setup_welcome_view(self):
        """Setup the welcome view shown when no messages are present"""
        # Clear existing widgets from chat layout
        while self.chat_layout.count():
            item = self.chat_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        
        # Create welcome widget
        welcome_widget = QWidget()
        welcome_layout = QVBoxLayout(welcome_widget)
        welcome_layout.setContentsMargins(0, 0, 0, 0)
        welcome_layout.setAlignment(Qt.AlignHCenter | Qt.AlignCenter)
        welcome_layout.setSpacing(0)
        
        # Main title with high-quality rendering
        title = QLabel("What can I help with?")
        title.setStyleSheet(f"""
            color: {CHATGPT_TEXT_COLOR};
            font-size: 32px;
            font-weight: 600;
            font-family: {FONT_FAMILY};
        """)
        title.setAlignment(Qt.AlignCenter)
        welcome_layout.addWidget(title)
        
        self.chat_layout.addWidget(welcome_widget)
        
        # When in welcome view, center the input bar with larger margins
        # Only update if the attribute exists (to avoid startup errors)
        if hasattr(self, 'input_layout'):
            self.input_layout.setContentsMargins(120, 10, 120, 24)
    
    def eventFilter(self, obj, event):
        """Event filter for handling key presses in message input"""
        if obj is self.message_input and event.type() == event.KeyPress:
            if event.key() == Qt.Key_Return and not event.modifiers() & Qt.ShiftModifier:
                self.send_message()
                return True
        return super().eventFilter(obj, event)
    
    def title_clicked(self, event):
        """Handle clicks on the header title by showing model dialog"""
        self.show_model_dialog()
    
    def show_system_prompt_dialog(self):
        """Show dialog for configuring system prompt"""
        dialog = SystemPromptDialog(self, self.system_prompt, self.use_streaming)
        if dialog.exec_():
            self.system_prompt = dialog.system_prompt
            self.use_streaming = dialog.use_streaming
            
            # Update the button to show if a system prompt is active
            if self.system_prompt:
                self.system_prompt_btn.setText("⚙️ *")
                self.system_prompt_btn.setToolTip(f"System Prompt Active: {self.system_prompt[:30]}...")
            else:
                self.system_prompt_btn.setText("⚙️")
                self.system_prompt_btn.setToolTip("Configure System Prompt")
    
    def add_streaming_bubble(self, message, is_user=False):
        """Add a chat bubble for streaming responses"""
        # Create a chat bubble for the first chunk
        bubble = ChatBubble(message, is_user)
        
        # Store the bubble for further updates
        self.current_streaming_bubble = bubble
        
        # Add the bubble to the chat layout
        bubble.setWindowOpacity(1.0)  # No fade-in for streaming
        self.chat_layout.addWidget(bubble)
        
        # Add to conversation history
        self.conversation_history.append({"role": "assistant", "content": message})
        
        # Scroll to the bottom
        self.smooth_scroll_to_bottom()
        
        return bubble
    
    def update_streaming_bubble(self, new_chunk):
        """Update the content of the streaming bubble with new text"""
        if self.current_streaming_bubble:
            # Get the current content from conversation history
            current_content = self.conversation_history[-1]["content"]
            
            # Add the new chunk
            updated_content = current_content + new_chunk
            
            # Update conversation history
            self.conversation_history[-1]["content"] = updated_content
            
            # Create a new bubble with the updated content
            new_bubble = ChatBubble(updated_content, False)
            
            # Replace the old bubble
            layout_index = self.chat_layout.indexOf(self.current_streaming_bubble)
            if layout_index >= 0:
                # Remove old bubble
                self.chat_layout.removeWidget(self.current_streaming_bubble)
                self.current_streaming_bubble.deleteLater()
                
                # Add new bubble at same position
                self.chat_layout.insertWidget(layout_index, new_bubble)
                self.current_streaming_bubble = new_bubble
            
            # Scroll to the bottom
            self.smooth_scroll_to_bottom()
        else:
            # If no streaming bubble exists yet, create one
            self.add_streaming_bubble(new_chunk, False)
            
    def handle_streaming_chunk(self, chunk):
        """Handle a streaming chunk from the API"""
        print(f"Received streaming chunk: {len(chunk)} chars")
        
        if self.current_streaming_bubble:
            self.update_streaming_bubble(chunk)
        else:
            self.add_streaming_bubble(chunk, False)
    
    def show_model_dialog(self):
        """Show dialog for selecting a model"""
        dialog = ModelSelectionDialog(self, self.api_url)
        if dialog.exec_():
            # Update settings from dialog
            self.api_url = dialog.api_url
            self.current_model = dialog.selected_model
            # Update the header title with just the formatted model name
            self.header_title.setText(dialog.display_name)
    
    def add_message_bubble(self, message, is_user=False):
        """Add a message bubble to the chat history"""
        # Check if this is the first message
        first_message = len(self.conversation_history) == 0
        
        # If this is the first message, clear the welcome screen with animation
        if first_message:
            # Clear existing widgets from chat layout
            while self.chat_layout.count():
                item = self.chat_layout.takeAt(0)
                if item.widget():
                    widget = item.widget()
                    # Create fade-out animation
                    fade_anim = QPropertyAnimation(widget, b"windowOpacity")
                    fade_anim.setDuration(200)
                    fade_anim.setStartValue(1.0)
                    fade_anim.setEndValue(0.0)
                    fade_anim.start()
                    # Schedule widget deletion after animation
                    QTimer.singleShot(200, widget.deleteLater)
            
            # Reset input margins back to original when we have messages
            self.input_layout.setContentsMargins(*self.original_input_margins)
        
        # Add the message bubble
        bubble = ChatBubble(message, is_user)
        
        # Animate the bubble appearance
        bubble.setWindowOpacity(0.0)
        self.chat_layout.addWidget(bubble)
        
        # Create fade-in animation
        fade_anim = QPropertyAnimation(bubble, b"windowOpacity")
        fade_anim.setDuration(200)
        fade_anim.setStartValue(0.0)
        fade_anim.setEndValue(1.0)
        fade_anim.start()
        
        # Scroll to the bottom with animation
        QTimer.singleShot(100, self.smooth_scroll_to_bottom)
    
    def smooth_scroll_to_bottom(self):
        """Smoothly scroll to the bottom of the chat"""
        scrollbar = self.scroll_area.verticalScrollBar()
        
        # Create scrolling animation
        scroll_anim = QPropertyAnimation(scrollbar, b"value")
        scroll_anim.setDuration(300)
        scroll_anim.setStartValue(scrollbar.value())
        scroll_anim.setEndValue(scrollbar.maximum())
        scroll_anim.setEasingCurve(QEasingCurve.OutCubic)
        scroll_anim.start()
    
    def send_message(self):
        """Send a message to the Ollama API"""
        try:
            message = self.message_input.toPlainText().strip()
            if not message:
                return
            
            # Check if this is a slash command
            if message.startswith('/'):
                # Try to process as command
                if self.command_handler.process_command(message):
                    self.message_input.clear()
                    return
            
            # Check if a model is selected
            if not self.current_model or self.current_model in ["No models found", "Fetching models...", "Error:"]:
                # Show model selection dialog
                self.show_model_dialog()
                if not self.current_model or self.current_model in ["No models found", "Fetching models...", "Error:"]:
                    self.add_message_bubble("Please select a valid model first.", is_user=False)
                    return
            
            # Clear input field
            self.message_input.clear()
            
            # Add user message to chat
            self.add_message_bubble(message, is_user=True)
            self.conversation_history.append({"role": "user", "content": message})
            
            # Change send button to show thinking state
            if hasattr(self, 'send_btn'):
                self.send_btn.setEnabled(False)
                self.send_btn.setText("⏳")
            
            print(f"Creating OllamaThread with model={self.current_model}, api_url={self.api_url}")
            print(f"System prompt is {'set' if self.system_prompt else 'not set'}")
            print(f"Streaming is {self.use_streaming}")
            
            # Reset streaming bubble if using streaming
            if self.use_streaming:
                self.current_streaming_bubble = None
            
            # Create thread for API request, including system prompt
            try:
                self.thread = OllamaThread(
                    self.current_model, 
                    message, 
                    self.api_url,
                    self.system_prompt,
                    self.use_streaming
                )
                
                # Connect signals
                self.thread.response_received.connect(self.handle_response)
                self.thread.error_occurred.connect(self.handle_error)
                
                # Connect streaming signal if using streaming
                if self.use_streaming:
                    self.thread.streaming_chunk_received.connect(self.handle_streaming_chunk)
                
                # Start the thread
                print("Starting OllamaThread...")
                self.thread.start()
                print("OllamaThread started successfully")
                
            except Exception as thread_error:
                print(f"Error creating or starting thread: {str(thread_error)}")
                import traceback
                traceback.print_exc()
                self.add_message_bubble(f"Error: Could not start request: {str(thread_error)}", is_user=False)
                
                # Reset send button
                if hasattr(self, 'send_btn'):
                    self.send_btn.setEnabled(True)
                    self.send_btn.setText("▶")
                
        except Exception as e:
            print(f"Error in send_message: {str(e)}")
            import traceback
            traceback.print_exc()
            self.add_message_bubble(f"Error: {str(e)}", is_user=False)
            
            # Try to reset the send button if there was an error
            try:
                if hasattr(self, 'send_btn'):
                    self.send_btn.setEnabled(True)
                    self.send_btn.setText("▶")
            except:
                pass
    
    def handle_response(self, response):
        """Handle response from Ollama API"""
        try:
            print(f"Received response from Ollama: {len(response)} characters")
            
            # If we're using streaming and already have a bubble, just finalize it
            if self.use_streaming and self.current_streaming_bubble:
                # Reset the streaming bubble
                self.current_streaming_bubble = None
            else:
                # Add the response to chat
                self.add_message_bubble(response)
                self.conversation_history.append({"role": "assistant", "content": response})
            
            # Reset send button
            if hasattr(self, 'send_btn'):
                self.send_btn.setEnabled(True)
                self.send_btn.setText("▶")
                    
        except Exception as e:
            print(f"Error in handle_response: {str(e)}")
            import traceback
            traceback.print_exc()
    
    def handle_error(self, error_message):
        """Handle error from Ollama API"""
        try:
            print(f"Error from Ollama API: {error_message}")
            
            self.add_message_bubble(f"Error: {error_message}")
            
            # Reset streaming bubble if using streaming
            if self.use_streaming:
                self.current_streaming_bubble = None
            
            # Reset send button
            if hasattr(self, 'send_btn'):
                self.send_btn.setEnabled(True)
                self.send_btn.setText("▶")
                    
        except Exception as e:
            print(f"Error in handle_error: {str(e)}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    try:
        app = QApplication(sys.argv)
        app.setStyle("Fusion")  # Use Fusion style for consistent look across platforms
        
        # Enable high DPI scaling for better text rendering
        app.setAttribute(Qt.AA_UseHighDpiPixmaps)
        app.setAttribute(Qt.AA_EnableHighDpiScaling)
        
        # Set application-wide attributes for antialiasing
        app.setDesktopSettingsAware(False)
        
        print("Starting Ollama Chat GUI...")
        window = OllamaChatGUI()
        print("Window created, showing application...")
        window.show()
        sys.exit(app.exec_())
    except Exception as e:
        print(f"Error starting application: {str(e)}")
        import traceback
        traceback.print_exc()
        input("Press Enter to exit...")
