import os
import asyncio
import logging
import streamlit as st
from mcp_host import UniversalMCPHost
from llm_clients import OpenAIClient, ClaudeClient, OllamaClient
from dotenv import load_dotenv

import nest_asyncio

load_dotenv()

from ui_components import (
    render_sidebar,
    render_chat_interface, 
    render_server_management,
    render_mcp_tools
)

# Enable nested asyncio for Streamlit
nest_asyncio.apply()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Page config
st.set_page_config(
    page_title="Universal MCP Host",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
st.markdown("""
<style>
    .main-header {
        font-size: 2.5rem;
        font-weight: bold;
        color: #1f77b4;
        text-align: center;
        margin-bottom: 2rem;
    }
    .server-status {
        padding: 0.5rem;
        margin: 0.25rem 0;
        border-radius: 0.5rem;
        font-weight: bold;
    }
    .server-connected {
        background-color: #d4edda;
        color: #155724;
        border: 1px solid #c3e6cb;
    }
    .server-disconnected {
        background-color: #f8d7da;
        color: #721c24;
        border: 1px solid #f5c6cb;
    }
    .tool-card {
        border: 1px solid #ddd;
        border-radius: 8px;
        padding: 1rem;
        margin: 0.5rem 0;
        background-color: #f8f9fa;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_resource
def get_mcp_host():
    """Initialize and cache the MCP host"""
    return UniversalMCPHost("config/servers.json")

@st.cache_resource
def get_llm_clients():
    """Initialize and cache LLM clients"""
    clients = {}
    
    # OpenAI
    if os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_API_KEY") != "your_openai_api_key_here":
        try:
            clients["gpt-4"] = OpenAIClient("gpt-4")
            clients["gpt-3.5-turbo"] = OpenAIClient("gpt-3.5-turbo")
            logger.info("✓ OpenAI models loaded")
        except Exception as e:
            logger.warning(f"Failed to initialize OpenAI client: {e}")
    
    # Claude
    if os.getenv("ANTHROPIC_API_KEY") and os.getenv("ANTHROPIC_API_KEY") != "your_anthropic_api_key_here":
        try:
            clients["claude-3-sonnet"] = ClaudeClient("claude-3-sonnet-20240229")
            clients["claude-3-haiku"] = ClaudeClient("claude-3-haiku-20240307")
            logger.info("✓ Claude models loaded")
        except Exception as e:
            logger.warning(f"Failed to initialize Claude client: {e}")
    
    # Ollama - Auto-detect available models
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        import requests
        response = requests.get(f"{ollama_base_url}/api/tags", timeout=5)
        if response.status_code == 200:
            models_data = response.json().get("models", [])
            ollama_models_loaded = 0
            
            for model_data in models_data:
                model_name = model_data["name"]
                # Create a cleaner display name
                display_name = f"Ollama: {model_name}"
                clients[display_name] = OllamaClient(model_name, ollama_base_url)
                ollama_models_loaded += 1
            
            if ollama_models_loaded > 0:
                logger.info(f"✓ Ollama models loaded: {ollama_models_loaded} models")
                st.success(f"🦙 Ollama connected! {ollama_models_loaded} models available")
        else:
            logger.warning("Ollama server not responding")
            
    except Exception as e:
        logger.warning(f"Ollama not available: {e}")
        st.info("🦙 Ollama not detected. Make sure Ollama is running: `ollama serve`")
    
    if not clients:
        st.warning("⚠️ No LLM clients configured. Please set up at least one:")
        st.write("- Install Ollama and run `ollama serve`")
        st.write("- Add OpenAI API key to config/.env")
        st.write("- Add Anthropic API key to config/.env")
    
    return clients

def main():
    """Main application entry point"""
    
    # Header
    st.markdown('<h1 class="main-header">🤖 Universal MCP Host</h1>', unsafe_allow_html=True)
    
def main():
    """Main application entry point"""
    
    # Header
    st.markdown('<h1 class="main-header">🤖 Universal MCP Host</h1>', unsafe_allow_html=True)
    
    # Initialize session state
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "mcp_host" not in st.session_state:
        st.session_state.mcp_host = get_mcp_host()
    if "llm_clients" not in st.session_state:
        st.session_state.llm_clients = get_llm_clients()
    if "selected_model" not in st.session_state:
        st.session_state.selected_model = list(st.session_state.llm_clients.keys())[0] if st.session_state.llm_clients else None
    if "mcp_host_started" not in st.session_state:
        st.session_state.mcp_host_started = False

    # Start MCP host only once
    if not st.session_state.mcp_host_started:
        with st.spinner("🚀 Starting MCP Host..."):
            try:
                asyncio.run(st.session_state.mcp_host.start())
                st.session_state.mcp_host_started = True
            except Exception as e:
                st.error(f"❌ Failed to start MCP Host: {e}")
                return
            except Exception as e:
                st.error(f"❌ Failed to start MCP Host: {e}")
                return

    # Show main interface
    render_main_interface()

def render_main_interface():
    """Render the main application interface"""
    # Sidebar
    render_sidebar()
    
    # Main content tabs
    tab1, tab2, tab3 = st.tabs(["💬 Chat", "🔧 Server Management", "🛠️ MCP Tools"])
    
    with tab1:
        render_chat_interface()
    
    with tab2:
        render_server_management()
    
    with tab3:
        render_mcp_tools()

if __name__ == "__main__":
    main()
