# Local MCP Host

A modern, full-featured Model Context Protocol (MCP) host with React frontend, FastAPI backend, and comprehensive multi-LLM support.

## 🚀 Features

### **Multi-LLM Support**
- 🤖 **OpenAI**: GPT-4, GPT-4 Turbo, GPT-3.5 Turbo
- 🎯 **Anthropic**: Claude 3.5 Sonnet, Claude 3 Sonnet, Claude 3 Haiku  
- 🦙 **Ollama**: Auto-discovers all local models
- 🔄 **Real-time Model Switching**: Change models mid-conversation

### **Universal MCP Server Support**
- 🔌 **STDIO & SSE Transports**: Local and remote server connections
- 🛠️ **Popular Servers**: Filesystem, SQLite, Git, and more
- ➕ **Add Servers via UI**: No config file editing required
- ⚡ **Auto-reconnection**: Robust connection management

### **Modern Web Interface**
- 💬 **Rich Chat**: Markdown rendering with syntax highlighting
- 📊 **Tools Browser**: Comprehensive tool discovery and documentation
- 🔧 **Interactive Testing**: Execute MCP tools with parameter forms
- 📱 **Responsive Design**: Works on desktop and mobile

### **Advanced Capabilities**
- 🧠 **Intelligent Tool Use**: LLMs automatically discover and use available tools
- 💾 **Persistent State**: Chat history and model selection preserved across tabs
- 🔍 **Real-time Search**: Find tools across all connected servers
- 📋 **Parameter Documentation**: Auto-generated schema documentation

## 📋 Requirements

- **Python 3.8+**
- **Node.js 16+**
- **npm or yarn**

## 🚀 Quick Start

### 1. Clone and Setup
```bash
git clone <repository-url>
cd universal-mcp-host
```

### 2. Start the Application
```bash
./start.sh
```

This script will:
- Install Python and Node.js dependencies
- Start the FastAPI backend on port 8000
- Start the React frontend on port 3000
- Display live logs from both services

### 3. Configure LLM Providers (Optional)

Create `config/.env` with your API keys:
```bash
# OpenAI (optional)
OPENAI_API_KEY=sk-your-openai-key

# Anthropic Claude (optional)
ANTHROPIC_API_KEY=sk-ant-your-claude-key

# Ollama (runs locally, no key needed)
OLLAMA_BASE_URL=http://localhost:11434
```

### 4. Access the Interface

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Documentation**: http://localhost:8000/docs

## 🔧 Adding MCP Servers

### Via Web Interface (Recommended)

1. Go to the **Servers** tab
2. Click **"Add Server"**
3. Fill in the server details
4. Click **"Add Server"** to connect

### Popular Server Examples

**Filesystem Access:**
- **Command**: `npx`
- **Args**: `-y @modelcontextprotocol/server-filesystem /path/to/directory`

**SQLite Database:**
- **Command**: `uvx`
- **Args**: `mcp-server-sqlite --db-path /path/to/database.db`

**Git Repository:**
- **Command**: `npx`
- **Args**: `-y @modelcontextprotocol/server-git /path/to/repo`

**Brave Search:**
- **Command**: `uvx`
- **Args**: `mcp-server-brave-search`

### Manual Configuration

Edit `config/servers.json`:
```json
{
  "servers": {
    "filesystem": {
      "type": "stdio",
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
      "description": "File system operations"
    },
    "sqlite": {
      "type": "stdio", 
      "command": "uvx",
      "args": ["mcp-server-sqlite", "--db-path", "/tmp/test.db"],
      "description": "SQLite database access"
    },
    "github": {
      "type": "sse",
      "url": "https://your-github-mcp-server.com/sse",
      "headers": {
        "Authorization": "Bearer YOUR_TOKEN"
      },
      "description": "GitHub repository access"
    }
  }
}
```

## 💬 Using the Chat Interface

### Basic Usage
1. Select your preferred LLM model from the dropdown
2. Start chatting! The AI can automatically discover and use MCP tools
3. Your conversation and model selection persist across tab switches

### Example Prompts
- "List files in the /tmp directory"
- "Read the contents of package.json"
- "Search the codebase for TODO comments"
- "Query the database for user records"
- "Create a new file with some content"

### Advanced Features
- **Markdown Support**: Code blocks, lists, and formatting render properly
- **Tool Introspection**: Ask "What tools do you have access to?"
- **Multi-step Operations**: "Analyze all Python files and create a summary"

## 🛠️ Tools Management

### Browse Tools Tab
- **Complete Tool Listing**: See all tools from all connected servers
- **Parameter Documentation**: View required/optional parameters with descriptions
- **Server Organization**: Tools grouped by server with visual indicators
- **Quick Testing**: Click "Try It" to jump to the execution interface

### Execute Tools Tab
- **Interactive Forms**: Dynamic parameter forms based on tool schemas
- **JSON Validation**: Real-time validation of tool arguments
- **Result Display**: Formatted output with syntax highlighting
- **Error Handling**: Clear error messages with debugging info

## 🏗️ Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   React Frontend│ ── │  FastAPI Backend │ ── │   LLM Providers │
│   (Port 3000)   │    │   (Port 8000)    │    │  OpenAI/Claude  │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                              │                          │
                              ▼                          ▼
                    ┌──────────────────┐         ┌─────────────┐
                    │  Simple MCP Host │         │   Ollama    │
                    │                  │         │ (Local LLMs)│
                    └──────────────────┘         └─────────────┘
                              │
                              ▼
                    ┌──────────────────┐
                    │   MCP Servers    │
                    │ ┌──────────────┐ │
                    │ │ Filesystem   │ │
                    │ │ SQLite       │ │
                    │ │ Git          │ │
                    │ │ Custom...    │ │
                    │ └──────────────┘ │
                    └──────────────────┘
```

## 📁 Project Structure

```
universal-mcp-host/
├── frontend/                 # React application
│   ├── src/
│   │   ├── App.js            # Main application component
│   │   ├── ChatInterface.js  # Chat UI with markdown support
│   │   ├── MCPTools.js       # Tools browser and executor
│   │   ├── ModelSelector.js  # LLM model selection
│   │   └── AddServerModal.js # Server configuration modal
│   └── package.json          # Frontend dependencies
│
├── backend/                  # FastAPI application
│   ├── main.py              # API server and endpoints
│   ├── requirements.txt     # Backend dependencies
│   └── venv/               # Python virtual environment
│
├── src/                     # Core MCP implementation
│   ├── simple_mcp_host.py  # Robust MCP client implementation
│   ├── mcp_host.py          # Original MCP host (fallback)
│   └── llm_clients.py       # Multi-provider LLM clients
│
├── config/                  # Configuration files
│   ├── servers.json         # MCP server definitions
│   ├── .env                 # Environment variables (create this)
│   └── .env.example         # Environment template
│
├── start.sh           # Startup script
└── README.md               # This file
```

## 🔧 Development

### Backend Development
```bash
cd backend
source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### Frontend Development
```bash
cd frontend
npm install
npm start
```

### Adding New LLM Providers
1. Extend `BaseLLMClient` in `src/llm_clients.py`
2. Add provider detection in `backend/main.py`
3. Update model selector UI in `frontend/src/ModelSelector.js`

### Adding New MCP Transports
1. Extend transport support in `src/simple_mcp_host.py`
2. Update server configuration schema
3. Add UI forms in `frontend/src/AddServerModal.js`

## 🐛 Troubleshooting

### Common Issues

**MCP Server Won't Connect:**
- Check server command and arguments
- Verify the server executable is available
- Review server logs in the terminal
- Ensure proper permissions for file access

**No LLM Models Available:**
- Configure API keys in `config/.env`
- For Ollama: ensure it's running (`ollama serve`)
- Check network connectivity for cloud providers

**Tools Not Working:**
- Verify MCP server is properly connected
- Check tool arguments match expected schema
- Review server permissions and access rights

**Frontend Build Errors:**
- Delete `node_modules` and run `npm install`
- Check Node.js version (16+ required)
- Clear browser cache and reload

### Debug Mode
Enable detailed logging:
```bash
export MCP_LOG_LEVEL=DEBUG
./start.sh
```

### Reset Configuration
```bash
# Backup current config
cp config/servers.json config/servers.json.backup

# Reset to minimal config
echo '{"servers": {}}' > config/servers.json
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes with tests
4. Submit a pull request

## 📚 Resources

- [MCP Specification](https://modelcontextprotocol.io/specification)
- [Official MCP Servers](https://github.com/modelcontextprotocol)
- [Community MCP Registry](https://mcpservers.org/)
- [FastAPI Documentation](https://fastapi.tiangolo.com/)
- [React Documentation](https://react.dev/)

## 📄 License

MIT License - see LICENSE file for details.

---

## 🎯 What Makes This Special

- **Production Ready**: Robust error handling, reconnection logic, and comprehensive logging
- **User Friendly**: No command-line required - manage everything through the web interface
- **Developer Friendly**: Clear architecture, extensive documentation, and easy to extend
- **Multi-Modal**: Works with any LLM provider and any MCP server
- **Modern Stack**: React + FastAPI + TypeScript-style development experience

**Local MCP Host** - The complete solution for MCP integration! 🚀✨
