# 🔥 ChatForge

**A Beautiful, Modern Desktop Chat Interface for Ollama**

ChatForge is a sleek, ChatGPT-inspired desktop application that brings the power of Ollama's local language models to an intuitive, feature-rich interface. Built with PyQt5, it offers a smooth, responsive chat experience with advanced features like streaming responses, custom system prompts, and intelligent model management.

## Demo
![ChatForge Interface](https://i.ibb.co/jxyCckM/image-2025-06-22-113534991.png)

![Python](https://img.shields.io/badge/Python-3.7+-green)
![License](https://img.shields.io/badge/License-MIT-orange)

## ✨ Features

### 🎨 **Modern UI Design**
- **ChatGPT-inspired interface** with dark theme
- **Smooth animations** and transitions
- **Responsive layout** that adapts to window size
- **High-quality font rendering** with improved antialiasing

### 🚀 **Advanced Chat Experience**
- **Real-time streaming responses** for immediate feedback
- **Markdown rendering** with syntax highlighting for code blocks
- **Message interaction** with copy, thumbs up/down buttons
- **Smooth auto-scrolling** to latest messages

### 🛠️ **Powerful Features**
- **Intelligent model selection** with grouped, organized display
- **Custom system prompts** with template variables (`%model%`, `%parameters%`)
- **Slash commands** for quick actions (`/clear`, `/models`, `/system`, `/bye`)
- **Command prediction** with auto-complete popup
- **Configuration persistence** across sessions

### 🎯 **Model Management**
- **Automatic model detection** from your Ollama installation
- **Smart model naming** with proper capitalization and formatting
- **Model grouping** by family (Llama, Mistral, CodeLlama, etc.)
- **Parameter count display** for easy model comparison

## 📋 Requirements

### System Requirements
- **Python 3.7+**
- **Ollama installed and running** (download from [ollama.ai](https://ollama.ai))
- **Operating System**: Windows, macOS, or Linux

### Python Dependencies
```
PyQt5>=5.15.0
requests>=2.25.0
markdown>=3.3.0
```

## 🚀 Installation

### 1. Clone the Repository
```bash
git clone https://github.com/yourusername/chatforge.git
cd chatforge
```

### 2. Install Dependencies
```bash
pip install PyQt5 requests markdown
```

### 3. Ensure Ollama is Running
Make sure Ollama is installed and running on your system:
```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# If not installed, download from https://ollama.ai
# Then pull a model, for example:
ollama pull llama2
```

### 4. Launch ChatForge
```bash
python chatforge.py
```

## 🎮 Usage

### First Time Setup
1. **Launch the application** - ChatForge will automatically prompt you to select a model
2. **Choose your model** from the organized tree view
3. **Configure API URL** if Ollama is running on a different port
4. **Start chatting!**

### Chat Interface
- **Type your message** in the input box at the bottom
- **Send with Enter** (Shift+Enter for new lines)
- **Use the send button** (▶) or keyboard shortcut

### Slash Commands
ChatForge supports several built-in commands:

| Command | Description |
|---------|-------------|
| `/clear` | Clear the chat history |
| `/models` | Open model selection dialog |
| `/system` | Configure system prompt |
| `/bye` | Exit the application |

### System Prompts
Create custom system prompts to guide your AI's behavior:

1. **Click the settings icon** (⚙️) in the top-right
2. **Enter your system prompt** with optional template variables:
   - `%model%` - Replaced with current model name
   - `%parameters%` - Replaced with parameter count
3. **Enable streaming** for real-time responses
4. **Save configuration** - persists across sessions

### Model Selection
- **Click the title** in the header to change models
- **Browse models** organized by family (Llama, Mistral, etc.)
- **See parameter counts** and model variants at a glance
- **Refresh models** to detect newly installed ones

## ⚙️ Configuration

ChatForge automatically saves your preferences to `ollama_config.json`:

```json
{
    "system_prompt": "You are a helpful assistant...",
    "use_streaming": true
}
```

### Customization Options
- **API URL**: Change if Ollama runs on different host/port
- **System Prompts**: Set persistent instructions for your AI
- **Streaming**: Toggle real-time vs. complete responses

## 🎨 Interface Overview

### Welcome Screen
- **Clean, centered layout** when no messages are present
- **"What can I help with?"** prompt
- **Centered input box** for focused interaction

### Chat Messages
- **User messages**: Right-aligned, clean typography
- **AI responses**: Left-aligned with interaction buttons
- **Markdown support**: Code blocks, tables, lists, links
- **Copy functionality**: Easy text copying with clipboard integration

### Header
- **Clickable title**: Shows current model, click to change
- **Settings button**: Quick access to system prompt configuration
- **Clean, minimal design**: Focus on conversation

## 🐛 Troubleshooting

### Common Issues

**"No models found"**
- Ensure Ollama is running: `ollama serve`
- Check that you have models installed: `ollama list`
- Verify API URL in model selection dialog

**Connection refused**
- Confirm Ollama is running on the correct port (default: 11434)
- Check firewall settings
- Try updating the API URL in settings

**Import errors**
- Install all required dependencies: `pip install PyQt5 requests markdown`
- Ensure you're using Python 3.7 or higher

**UI rendering issues**
- Try running with different Qt styles
- Update your graphics drivers
- Ensure proper display scaling settings

### Performance Tips
- **Use streaming** for better perceived performance with long responses
- **Clear chat history** periodically with `/clear` command
- **Choose appropriate models** based on your hardware capabilities

## 🤝 Contributing

We welcome contributions! Here's how you can help:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/amazing-feature`
3. **Commit your changes**: `git commit -m 'Add amazing feature'`
4. **Push to branch**: `git push origin feature/amazing-feature`
5. **Open a Pull Request**

### Development Setup
```bash
# Clone your fork
git clone https://github.com/yourusername/chatforge.git

# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
python -m pytest tests/
```

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- **Ollama team** for the excellent local LLM platform
- **OpenAI** for ChatGPT UI inspiration
- **Qt/PyQt** for the robust GUI framework
- **Python-Markdown** for beautiful text rendering

## 🔗 Links

- **Ollama**: [https://ollama.ai](https://ollama.ai)
- **PyQt5 Documentation**: [https://doc.qt.io/qtforpython/](https://doc.qt.io/qtforpython/)
- **Report Issues**: [GitHub Issues](https://github.com/yourusername/chatforge/issues)

---

**Built with ❤️ for the open-source AI community**

*ChatForge - Where conversations are crafted, not just generated.*
