#!/usr/bin/env python3
"""
FastAPI backend for Universal MCP Host
Handles MCP server connections asynchronously with LLM integration
"""

import logging
import json
import re
import os
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn

# Import our existing MCP classes
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from mcp_host import UniversalMCPHost, MCPServerConfig
from simple_mcp_host import SimpleMCPHost  # Import the simpler implementation
from llm_clients import create_llm_client, LLMMessage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Universal MCP Host API", version="1.0.0")

# Enable CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global MCP host and LLM client instances
mcp_host: Optional[UniversalMCPHost] = None
llm_client = None

def get_available_models():
    """Get list of available LLM models"""
    models = []
    
    # Check OpenAI
    if os.getenv("OPENAI_API_KEY") and os.getenv("OPENAI_API_KEY") != "your_openai_api_key_here":
        models.extend([
            {"id": "openai_gpt-4", "name": "GPT-4", "provider": "OpenAI", "description": "Most capable OpenAI model"},
            {"id": "openai_gpt-4-turbo", "name": "GPT-4 Turbo", "provider": "OpenAI", "description": "Fast and capable"},
            {"id": "openai_gpt-3.5-turbo", "name": "GPT-3.5 Turbo", "provider": "OpenAI", "description": "Fast and efficient"},
        ])
    
    # Check Claude
    if os.getenv("ANTHROPIC_API_KEY") and os.getenv("ANTHROPIC_API_KEY") != "your_anthropic_api_key_here":
        models.extend([
            {"id": "claude_claude-3-5-sonnet-20241022", "name": "Claude 3.5 Sonnet", "provider": "Anthropic", "description": "Latest and most capable Claude model"},
            {"id": "claude_claude-3-sonnet-20240229", "name": "Claude 3 Sonnet", "provider": "Anthropic", "description": "Balanced performance"},
            {"id": "claude_claude-3-haiku-20240307", "name": "Claude 3 Haiku", "provider": "Anthropic", "description": "Fast and efficient"},
        ])
    
    # Check Ollama
    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
    try:
        import requests
        response = requests.get(f"{ollama_base_url}/api/tags", timeout=5)
        if response.status_code == 200:
            ollama_models = response.json().get("models", [])
            for model_data in ollama_models:
                model_name = model_data["name"]
                models.append({
                    "id": f"ollama_{model_name}",
                    "name": model_name,
                    "provider": "Ollama",
                    "description": "Local Ollama model"
                })
    except Exception as e:
        logger.warning(f"Could not fetch Ollama models: {e}")
    
    return models

def create_llm_client_by_id(model_id: str):
    """Create LLM client from model ID"""
    if model_id.startswith("openai_"):
        model_name = model_id.replace("openai_", "")
        return create_llm_client("openai", model_name)
    elif model_id.startswith("claude_"):
        model_name = model_id.replace("claude_", "")
        return create_llm_client("claude", model_name)
    elif model_id.startswith("ollama_"):
        model_name = model_id.replace("ollama_", "")
        return create_llm_client("ollama", model_name)
    else:
        raise ValueError(f"Unsupported model ID: {model_id}")

async def process_tool_request(user_message: str, chat_history: List[Dict], client=None) -> str:
    """Process user message and execute MCP tools if needed"""
    logger.info(f"Processing tool request: {user_message}")
    
    if not mcp_host:
        logger.error("MCP Host not available")
        return "MCP Host not available"
    
    # Get available tools from connected servers with detailed information
    available_tools = []
    for server_name, server in mcp_host.servers.items():
        if server.connected:
            for tool in server.tools:
                available_tools.append({
                    "name": tool.name,
                    "description": getattr(tool, 'description', f'Tool from {server_name}'),
                    "server": server_name,
                    "input_schema": getattr(tool, 'input_schema', {})
                })
    
    tool_strings = [f"{t['server']}.{t['name']}" for t in available_tools]
    logger.info(f"Available tools: {tool_strings}")
    
    if not available_tools:
        logger.warning("No MCP tools are currently available")
        return "No MCP tools are currently available. Please connect to MCP servers first."
    
    # Create detailed system prompt with actual available tools
    tools_list = []
    for tool in available_tools:
        schema_info = ""
        if tool['input_schema'].get('properties'):
            params = []
            for param, details in tool['input_schema']['properties'].items():
                param_type = details.get('type', 'string')
                param_desc = details.get('description', '')
                required = param in tool['input_schema'].get('required', [])
                req_marker = " (required)" if required else " (optional)"
                params.append(f"    - {param} ({param_type}){req_marker}: {param_desc}")
            if params:
                schema_info = f"\n" + "\n".join(params)
        
        tools_list.append(f"- {tool['server']}.{tool['name']}: {tool['description']}{schema_info}")

    system_prompt = f"""You are an AI assistant that can use MCP (Model Context Protocol) tools to help users.

AVAILABLE TOOLS:
{chr(10).join(tools_list)}

CRITICAL INSTRUCTIONS:
1. Use the EXACT tool names as listed above with the server prefix (e.g., filesystem.list_directory, NOT list_files)
2. For listing files/directories, use "list_directory" NOT "list_files"
3. Use proper JSON format with double quotes: {{"key": "value"}}

For tool execution, use this EXACT format:
TOOL_CALL: server_name.tool_name({{"parameter": "value"}})

EXAMPLES:
- To list files: TOOL_CALL: filesystem.list_directory({{"path": "/tmp"}})
- To read a file: TOOL_CALL: filesystem.read_file({{"path": "/path/to/file.txt"}})
- To get file info: TOOL_CALL: filesystem.get_file_info({{"path": "/path/to/file"}})

Always use double quotes in JSON and explain what you're doing."""

    # Convert chat history to LLM format
    llm_messages = [LLMMessage(role="system", content=system_prompt)]
    for msg in chat_history:
        llm_messages.append(LLMMessage(role=msg["role"], content=msg["content"]))
    llm_messages.append(LLMMessage(role="user", content=user_message))
    
    # Get LLM response
    if not client:
        # Try to get a default client
        available_models = get_available_models()
        if not available_models:
            logger.info("No LLM models available, using simple tool detection fallback")
            return await simple_tool_detection(user_message)
        
        client = create_llm_client_by_id(available_models[0]["id"])
    
    logger.info(f"LLM client: {client}")
    
    try:
        logger.info(f"Sending request to LLM with {len(llm_messages)} messages")
        response = await client.chat(llm_messages)
        response_text = response.content
        logger.info(f"LLM response: {response_text[:200]}...")
        
        # Look for tool calls in the response and handle malformed JSON
        tool_calls = re.findall(r'TOOL_CALL:\s*(\w+)\.(\w+)\((.+?)\)', response_text)
        logger.info(f"Found {len(tool_calls)} tool calls: {tool_calls}")
        
        if tool_calls:
            # Execute tools and replace calls with results
            for server_name, tool_name, args_str in tool_calls:
                try:
                    # Clean up the JSON - fix common issues
                    cleaned_args = args_str.strip()
                    # Replace single quotes with double quotes for JSON
                    cleaned_args = re.sub(r"(\w+):", r'"\1":', cleaned_args)  # Fix unquoted keys
                    cleaned_args = cleaned_args.replace("'", '"')  # Fix single quotes
                    
                    logger.info(f"Cleaned args: {cleaned_args}")
                    args = json.loads(cleaned_args)
                    
                    if server_name in mcp_host.servers and mcp_host.servers[server_name].connected:
                        result = await mcp_host.servers[server_name].call_tool(tool_name, args)
                        result_text = json.dumps(result.get("content", result), indent=2)
                        
                        # Replace the tool call with the result
                        old_call = f"TOOL_CALL: {server_name}.{tool_name}({args_str})"
                        new_text = f"**Executed {tool_name} on {server_name}:**\n```json\n{result_text}\n```"
                        response_text = response_text.replace(old_call, new_text)
                    else:
                        error_msg = f"**Error: Server {server_name} not available**"
                        old_call = f"TOOL_CALL: {server_name}.{tool_name}({args_str})"
                        response_text = response_text.replace(old_call, error_msg)
                        
                except json.JSONDecodeError as e:
                    error_msg = f"**Error executing {tool_name}:** Invalid JSON arguments: {str(e)}"
                    old_call = f"TOOL_CALL: {server_name}.{tool_name}({args_str})"
                    response_text = response_text.replace(old_call, error_msg)
                    logger.error(f"JSON decode error for {tool_name}: {e}")
                except Exception as e:
                    error_msg = f"**Error executing {tool_name}:** {str(e)}"
                    old_call = f"TOOL_CALL: {server_name}.{tool_name}({args_str})"
                    response_text = response_text.replace(old_call, error_msg)
                    logger.error(f"Tool execution error for {tool_name}: {e}")
        
        return response_text
        
    except Exception as e:
        logger.error(f"LLM processing error: {e}")
        return await simple_tool_detection(user_message)

async def simple_tool_detection(user_message: str) -> str:
    """Simple fallback tool detection without LLM"""
    if not mcp_host:
        return "MCP Host not available"
    
    message_lower = user_message.lower()
    
    # Simple pattern matching for common requests
    if any(word in message_lower for word in ['list', 'files', 'directory', 'folder']):
        # Try to execute list_files
        for server_name, server in mcp_host.servers.items():
            if server.connected:
                for tool in server.tools:
                    if tool.name == 'list_files':
                        try:
                            # Extract path if mentioned, default to /tmp
                            path = "/tmp"
                            if "in" in message_lower:
                                # Try to extract path after "in"
                                parts = message_lower.split("in")
                                if len(parts) > 1:
                                    potential_path = parts[-1].strip()
                                    if potential_path.startswith('/'):
                                        path = potential_path.split()[0]
                            
                            result = await server.call_tool('list_files', {"path": path})
                            result_text = json.dumps(result.content if hasattr(result, 'content') else result, indent=2)
                            return f"I found these files in {path}:\n```json\n{result_text}\n```"
                        except Exception as e:
                            return f"Error listing files: {str(e)}"
    
    elif any(word in message_lower for word in ['read', 'show', 'content', 'file']):
        return "I can help you read files! Please specify the full path to the file you'd like me to read."
    
    # Default response
    connected_servers = [name for name, server in mcp_host.servers.items() if server.connected]
    available_tools = []
    for server_name, server in mcp_host.servers.items():
        if server.connected:
            for tool in server.tools:
                available_tools.append(f"{server_name}.{tool.name}")
    
    return f"""I'm ready to help you with MCP tools!

Connected servers: {', '.join(connected_servers) if connected_servers else 'None'}
Available tools: {', '.join(available_tools) if available_tools else 'None'}

You can ask me to:
- List files in a directory
- Read file contents  
- Execute any available MCP tool

What would you like me to do?"""

# Pydantic models
class ServerResponse(BaseModel):
    name: str
    protocol: str
    command: str
    status: str
    tools_count: int = 0
    resources_count: int = 0
    prompts_count: int = 0

class ConnectResponse(BaseModel):
    success: bool
    message: str

class ModelInfo(BaseModel):
    id: str
    name: str
    provider: str
    description: Optional[str] = None

class ChatMessage(BaseModel):
    role: str
    content: str

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []
    model: Optional[str] = None  # Allow model selection

class ModelSelectionRequest(BaseModel):
    model_id: str

class ChatResponse(BaseModel):
    response: str

class ToolRequest(BaseModel):
    arguments: Dict = {}

class ToolResponse(BaseModel):
    result: Dict = {}
    error: Optional[str] = None

@app.on_event("startup")
async def startup_event():
    """Initialize MCP host on startup"""
    global mcp_host
    try:
        # Initialize MCP host with absolute path
        config_path = Path(__file__).parent.parent / "config" / "servers.json"
        logger.info(f"Loading MCP config from: {config_path}")
        
        # Use the simple implementation as primary approach
        # The official MCP SDK has known issues with TaskGroups and BrokenResourceError
        logger.info("Using Simple MCP implementation for better stability...")
        mcp_host = SimpleMCPHost(str(config_path))
        logger.info(f"Simple MCP Host initialized with {len(mcp_host.servers)} servers")
        
        # Log server names for debugging
        for server_name in mcp_host.servers.keys():
            logger.info(f"Loaded server: {server_name}")
        
        await mcp_host.start()
        logger.info("Simple MCP Host started")
        
        # Log connection status
        success_count = 0
        for status in mcp_host.get_server_statuses():
            if status.connected:
                logger.info(f"✅ Server {status.name} connected with {len(status.tools)} tools")
                for tool in status.tools:
                    logger.info(f"  - Tool: {tool.name}")
                success_count += 1
            else:
                logger.warning(f"❌ Server {status.name} failed to connect")
        
        if success_count > 0:
            logger.info(f"🎉 MCP Host startup successful! {success_count} server(s) connected")
        else:
            logger.warning("⚠️ No MCP servers connected, but system will continue")
                    
    except Exception as e:
        logger.error(f"Failed to start MCP Host: {e}")
        import traceback
        logger.error(f"Full traceback:\n{traceback.format_exc()}")
        # Continue without MCP host for now

@app.get("/api/servers", response_model=List[ServerResponse])
async def get_servers():
    """Get list of all MCP servers and their status"""
    logger.info(f"GET /api/servers called. MCP host: {mcp_host is not None}")
    
    if not mcp_host:
        logger.error("MCP Host not initialized")
        raise HTTPException(status_code=500, detail="MCP Host not initialized")
    
    logger.info(f"Number of servers in mcp_host: {len(mcp_host.servers)}")
    
    servers = []
    for server_name, server_manager in mcp_host.servers.items():
        logger.info(f"Processing server: {server_name}, connected: {server_manager.connected}")
        status = "connected" if server_manager.connected else "disconnected"
        
        try:
            # Handle both SimpleMCPServer and RealMCPServer
            if hasattr(server_manager, 'config'):
                # RealMCPServer
                command = server_manager.config.command or ""
                protocol = server_manager.config.type.value
            else:
                # SimpleMCPServer
                command = server_manager.command or ""
                protocol = "stdio"
                
            server_response = ServerResponse(
                name=server_name,
                protocol=protocol,
                command=command,
                status=status,
                tools_count=len(server_manager.tools) if server_manager.connected else 0,
                resources_count=getattr(server_manager, 'resources', []) and len(getattr(server_manager, 'resources', [])) or 0,
                prompts_count=getattr(server_manager, 'prompts', []) and len(getattr(server_manager, 'prompts', [])) or 0
            )
            servers.append(server_response)
            logger.info(f"Added server {server_name} to response")
        except Exception as e:
            logger.error(f"Error processing server {server_name}: {e}")
    
    logger.info(f"Returning {len(servers)} servers")
    return servers

@app.post("/api/servers/{server_name}/connect", response_model=ConnectResponse)
async def connect_server(server_name: str):
    """Connect to a specific MCP server"""
    if not mcp_host:
        raise HTTPException(status_code=500, detail="MCP Host not initialized")
    
    if server_name not in mcp_host.servers:
        raise HTTPException(status_code=404, detail=f"Server '{server_name}' not found")
    
    try:
        server_manager = mcp_host.servers[server_name]
        success = await server_manager.connect()
        
        if success:
            return ConnectResponse(success=True, message=f"Connected to {server_name}")
        else:
            # Connection failed - return 500 with error details
            raise HTTPException(
                status_code=500, 
                detail=f"Failed to connect to {server_name}"
            )
            
    except HTTPException:
        # Re-raise HTTP exceptions
        raise
    except Exception as e:
        logger.error(f"Error connecting to {server_name}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error connecting to {server_name}: {str(e)}"
        )

@app.post("/api/servers/{server_name}/disconnect", response_model=ConnectResponse)
async def disconnect_server(server_name: str):
    """Disconnect from a specific MCP server"""
    if not mcp_host:
        raise HTTPException(status_code=500, detail="MCP Host not initialized")
    
    if server_name not in mcp_host.servers:
        raise HTTPException(status_code=404, detail=f"Server '{server_name}' not found")
    
    try:
        server_manager = mcp_host.servers[server_name]
        await server_manager.disconnect()
        return ConnectResponse(success=True, message=f"Disconnected from {server_name}")
        
    except Exception as e:
        logger.error(f"Error disconnecting from {server_name}: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Error disconnecting from {server_name}: {str(e)}"
        )

@app.post("/api/servers/add")
async def add_server(server_config: dict):
    """Add a new MCP server"""
    if not mcp_host:
        raise HTTPException(status_code=500, detail="MCP Host not initialized")
    
    try:
        # Read current config
        config_path = Path(__file__).parent.parent / "config" / "servers.json"
        with open(config_path, 'r') as f:
            config_data = json.load(f)
        
        # Add new server
        server_name = server_config['name']
        if server_name in config_data['servers']:
            raise HTTPException(status_code=400, detail=f"Server '{server_name}' already exists")
        
        # Format server config
        new_server = {
            "type": server_config['type'],
            "description": server_config.get('description', '')
        }
        
        if server_config['type'] == 'stdio':
            new_server['command'] = server_config['command']
            new_server['args'] = server_config.get('args', [])
        else:  # sse
            new_server['url'] = server_config['url']
            if server_config.get('headers'):
                new_server['headers'] = server_config['headers']
        
        config_data['servers'][server_name] = new_server
        
        # Save config
        with open(config_path, 'w') as f:
            json.dump(config_data, f, indent=2)
        
        # Reload MCP host
        mcp_host.reload_config()
        
        # Try to connect to the new server
        if hasattr(mcp_host, 'servers') and server_name in mcp_host.servers:
            await mcp_host.servers[server_name].connect()
        
        return {"success": True, "message": f"Server '{server_name}' added successfully"}
        
    except Exception as e:
        logger.error(f"Error adding server: {e}")
        raise HTTPException(status_code=500, detail=f"Error adding server: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "mcp_host_running": mcp_host is not None}

@app.get("/api/models", response_model=List[ModelInfo])
async def get_models():
    """Get list of available LLM models"""
    try:
        models = get_available_models()
        return models
    except Exception as e:
        logger.error(f"Error getting models: {e}")
        raise HTTPException(status_code=500, detail=f"Error getting models: {str(e)}")

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """Handle chat messages with intelligent MCP tool integration and model selection"""
    if not mcp_host:
        raise HTTPException(status_code=500, detail="MCP Host not initialized")
    
    try:
        # Use specified model or default to first available
        selected_model_id = request.model
        if not selected_model_id:
            available_models = get_available_models()
            if not available_models:
                return ChatResponse(response="No LLM models are currently available. Please configure at least one model provider.")
            selected_model_id = available_models[0]["id"]
        
        # Create client for selected model
        client = create_llm_client_by_id(selected_model_id)
        
        # Process the message with potential tool execution
        response_text = await process_tool_request(request.message, request.history, client)
        return ChatResponse(response=response_text)
        
    except Exception as e:
        logger.error(f"Chat error: {e}")
        return ChatResponse(response=f"Sorry, I encountered an error: {str(e)}")

@app.post("/api/servers/{server_name}/tools/{tool_name}", response_model=ToolResponse)
async def execute_tool(server_name: str, tool_name: str, request: ToolRequest):
    """Execute a tool on a specific MCP server"""
    if not mcp_host:
        raise HTTPException(status_code=500, detail="MCP Host not initialized")
    
    if server_name not in mcp_host.servers:
        raise HTTPException(status_code=404, detail=f"Server '{server_name}' not found")
    
    server_manager = mcp_host.servers[server_name]
    if not server_manager.connected:
        raise HTTPException(status_code=400, detail=f"Server '{server_name}' is not connected")
    
    try:
        result = await server_manager.call_tool(tool_name, request.arguments)
        return ToolResponse(result=result.content if hasattr(result, 'content') else result)
        
    except Exception as e:
        logger.error(f"Tool execution error: {e}")
        raise HTTPException(
            status_code=500, 
            detail=f"Tool execution failed: {str(e)}"
        )

@app.get("/api/servers/{server_name}/tools")
async def get_server_tools(server_name: str):
    """Get available tools for a specific server"""
    if not mcp_host:
        raise HTTPException(status_code=500, detail="MCP Host not initialized")
    
    if server_name not in mcp_host.servers:
        raise HTTPException(status_code=404, detail=f"Server '{server_name}' not found")
    
    server_manager = mcp_host.servers[server_name]
    if not server_manager.connected:
        return {"tools": []}
    
    return {
        "tools": [{"name": tool.name, "description": tool.description} for tool in server_manager.tools],
        "resources": [{"name": resource.name, "description": resource.description} for resource in server_manager.resources],
        "prompts": [{"name": prompt.name, "description": prompt.description} for prompt in server_manager.prompts]
    }

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, log_level="info")