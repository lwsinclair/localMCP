"""
UI Components for Universal MCP Host
"""

import asyncio
import json
import logging

import streamlit as st

from mcp_host import MCPServerConfig, ServerType
from llm_clients import LLMMessage

logger = logging.getLogger(__name__)

def render_sidebar():
    """Render the sidebar"""
    with st.sidebar:
        st.header("⚙️ Configuration")
        
        # Model selection
        st.subheader("🤖 LLM Model")
        if st.session_state.llm_clients:
            selected_model = st.selectbox(
                "Choose Model:",
                options=list(st.session_state.llm_clients.keys()),
                index=0 if st.session_state.selected_model not in st.session_state.llm_clients else 
                      list(st.session_state.llm_clients.keys()).index(st.session_state.selected_model)
            )
            st.session_state.selected_model = selected_model
        else:
            st.warning("No LLM clients configured.")
        
        # Server status
        st.subheader("🔌 MCP Servers")
        server_statuses = st.session_state.mcp_host.get_server_statuses()
        
        for status in server_statuses:
            status_text = "🟢 Connected" if status.connected else "🔴 Disconnected"
            st.markdown(f"**{status.name}**: {status_text}")
        
        # Refresh button
        if st.button("🔄 Refresh Servers"):
            try:
                st.session_state.mcp_host.reload_config()
                st.success("✅ Configuration reloaded!")
                st.rerun()
            except Exception as e:
                st.error(f"❌ Error reloading config: {e}")

def render_chat_interface():
    """Render the main chat interface"""
    st.header("💬 Chat with AI + MCP Tools")
    
    # Display chat messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Chat input
    if prompt := st.chat_input("Ask me anything! I can use MCP tools to help."):
        # Add user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Generate response
        with st.chat_message("assistant"):
            response_placeholder = st.empty()
            
            if st.session_state.selected_model and st.session_state.selected_model in st.session_state.llm_clients:
                try:
                    # Prepare messages for LLM
                    llm_messages = [
                        LLMMessage(role="system", content=get_system_prompt()),
                        *[LLMMessage(role=msg["role"], content=msg["content"]) 
                          for msg in st.session_state.messages]
                    ]
                    
                    # Get LLM response
                    client = st.session_state.llm_clients[st.session_state.selected_model]
                    loop = asyncio.get_event_loop()
                    future = asyncio.run_coroutine_threadsafe(client.chat(llm_messages), loop)
                    response = future.result(timeout=30)
                    
                    # Process tool requests
                    future2 = asyncio.run_coroutine_threadsafe(process_tool_requests(response.content), loop)
                    processed_response = future2.result(timeout=30)
                    
                    response_placeholder.markdown(processed_response)
                    st.session_state.messages.append({"role": "assistant", "content": processed_response})
                    
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    response_placeholder.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})
            else:
                error_msg = "No LLM model selected or configured."
                response_placeholder.error(error_msg)

def get_system_prompt() -> str:
    """Generate system prompt with available MCP tools"""
    tools_info = []
    all_tools = st.session_state.mcp_host.get_all_tools()
    
    for server_name, tool in all_tools:
        # Handle real MCP Tool objects
        tool_name = tool.name
        tool_description = tool.description
        
        tools_info.append(f"- {tool_name} (server: {server_name}): {tool_description}")
    
    tools_text = "\n".join(tools_info) if tools_info else "No tools available."
    
    return f"""You are a helpful AI assistant with access to MCP (Model Context Protocol) tools.

Available tools:
{tools_text}

IMPORTANT: When you want to use a tool, you MUST format it exactly like this:

[USE_TOOL: server_name.tool_name]
{{"parameter_name": "parameter_value"}}
[/USE_TOOL]

For example, to list files in a directory using the filesystem server:
[USE_TOOL: filesystem.read_directory]
{{"path": "/tmp"}}
[/USE_TOOL]

Always use the exact server name and tool name as shown above. If a tool requires no parameters, use an empty object: {{}}

When a user asks to list files, use the filesystem tools. When they ask about databases, use sqlite tools.
"""

async def process_tool_requests(response: str) -> str:
    """Process tool usage requests in the response"""
    import re
    
    # Pattern to match tool usage requests - more flexible
    tool_pattern = r'\[USE_TOOL:\s*([^.]+)\.([^\]]+)\]\s*(\{[^}]*\})\s*\[/USE_TOOL\]'
    
    async def replace_tool_call(match):
        server_name = match.group(1).strip()
        tool_name = match.group(2).strip()
        args_json = match.group(3).strip()
        
        try:
            # Parse arguments
            if args_json == "{}":
                args = {}
            else:
                args = json.loads(args_json)
            
            # Call the tool
            result = await st.session_state.mcp_host.call_tool(server_name, tool_name, args)
            
            # Format the result - handle MCP CallToolResult
            if hasattr(result, 'content') and result.content:
                if isinstance(result.content, list):
                    # Extract text from TextContent objects
                    text_parts = []
                    for item in result.content:
                        if hasattr(item, 'text'):
                            text_parts.append(item.text)
                        elif isinstance(item, dict) and "text" in item:
                            text_parts.append(item["text"])
                        else:
                            text_parts.append(str(item))
                    content_text = '\n'.join(text_parts)
                else:
                    content_text = str(result.content)
                    
                return f"\n\n**🔧 Tool Result ({server_name}.{tool_name}):**\n```\n{content_text}\n```\n"
            else:
                return f"\n\n**✅ Tool executed:** {server_name}.{tool_name} (no output)\n"
                
        except Exception as e:
            return f"\n\n**❌ Tool Error ({server_name}.{tool_name}):** {str(e)}\n"
    
    # Check if there are any tool calls to process
    matches = list(re.finditer(tool_pattern, response))
    if not matches:
        return response
    
    # Process each match
    processed = response
    for match in reversed(matches):  # Process in reverse to maintain positions
        replacement = await replace_tool_call(match)
        processed = processed[:match.start()] + replacement + processed[match.end():]
    
    return processed

def render_server_management():
    """Render server management interface"""
    st.header("🔧 MCP Server Management")
    
    # Add new server form
    with st.expander("➕ Add New Server"):
        with st.form("add_server"):
            col1, col2 = st.columns(2)
            
            with col1:
                server_name = st.text_input("Server Name")
                server_type = st.selectbox("Type", ["stdio", "sse"])
                
            with col2:
                if server_type == "stdio":
                    command = st.text_input("Command")
                    args = st.text_input("Arguments (comma-separated)")
                    env_vars = st.text_area("Environment Variables (JSON)", value="{}")
                else:
                    url = st.text_input("URL")
                    headers = st.text_area("Headers (JSON)", value="{}")
            
            description = st.text_input("Description (optional)")
            
            if st.form_submit_button("Add Server"):
                if not server_name:
                    st.error("Server name is required")
                elif server_name in st.session_state.mcp_host.servers:
                    st.error(f"Server '{server_name}' already exists")
                elif server_type == "stdio" and not command:
                    st.error("Command is required for STDIO servers")
                elif server_type != "stdio" and not url:
                    st.error("URL is required for SSE/HTTP servers")
                else:
                    try:
                        # Parse environment variables for STDIO
                        env_dict = None
                        if server_type == "stdio" and env_vars and env_vars != "{}":
                            env_dict = json.loads(env_vars)
                        
                        # Parse headers for SSE/HTTP
                        headers_dict = None
                        if server_type != "stdio" and headers and headers != "{}":
                            headers_dict = json.loads(headers)
                        
                        config = MCPServerConfig(
                            name=server_name,
                            type=ServerType(server_type),
                            command=command if server_type == "stdio" else None,
                            args=args.split(",") if server_type == "stdio" and args else None,
                            env=env_dict,
                            url=url if server_type != "stdio" else None,
                            headers=headers_dict,
                            description=description
                        )
                        
                        loop = asyncio.get_event_loop()
                        future = asyncio.run_coroutine_threadsafe(st.session_state.mcp_host.add_server(config), loop)
                        success = future.result(timeout=10)
                        if success:
                            st.success(f"✅ Added server: {server_name}")
                            st.rerun()
                        else:
                            st.error("❌ Failed to add server - check logs for details")
                            
                    except json.JSONDecodeError as e:
                        st.error(f"❌ Invalid JSON format: {e}")
                    except Exception as e:
                        st.error(f"❌ Error: {str(e)}")

def render_mcp_tools():
    """Render MCP tools browser"""
    st.header("🛠️ MCP Tools Browser")
    
    # Show server connection status first
    st.subheader("📡 Server Status")
    server_statuses = st.session_state.mcp_host.get_server_statuses()
    
    if not server_statuses:
        st.warning("No servers configured.")
        return
    
    for status in server_statuses:
        col1, col2, col3, col4 = st.columns([2, 1, 1, 1])
        
        with col1:
            status_icon = "🟢" if status.connected else "🔴"
            st.write(f"{status_icon} **{status.name}**")
        
        with col2:
            st.write(f"Tools: {len(status.tools)}")
        
        with col3:
            if st.button("🔄 Reconnect", key=f"reconnect_{status.name}"):
                print(f"DEBUG: Reconnect button clicked for {status.name}")
                st.write(f"🔄 Reconnect clicked for {status.name}")
                
                if status.name in st.session_state.mcp_host.servers:
                    print(f"DEBUG: Server {status.name} found in servers dict")
                    with st.spinner(f"Reconnecting to {status.name}..."):
                        try:
                            # Show what we're trying to connect to
                            server_manager = st.session_state.mcp_host.servers[status.name]
                            config = server_manager.config
                            
                            print(f"DEBUG: Config loaded for {status.name}: {config.type.value}")
                            
                            st.info(f"Attempting to connect to {status.name}...")
                            st.write(f"Type: {config.type.value}")
                            if config.command:
                                st.write(f"Command: {config.command}")
                                st.write(f"Args: {config.args}")
                            if config.url:
                                st.write(f"URL: {config.url}")
                            
                            print(f"DEBUG: About to call connect() for {status.name}")
                            
                            # Simple approach - just use asyncio.run
                            with st.spinner(f"Connecting to {status.name}..."):
                                success = asyncio.run(server_manager.connect())
                            if success:
                                st.success(f"✅ Successfully connected to {status.name}")
                            else:
                                st.error(f"❌ Failed to connect to {status.name}")
                                
                            st.rerun()
                            
                        except Exception as e:
                            print(f"DEBUG: Exception during reconnect: {e}")
                            st.error(f"❌ Connection error for {status.name}: {str(e)}")
                            import traceback
                            st.code(traceback.format_exc())
                else:
                    print(f"DEBUG: Server {status.name} NOT found in servers dict")
                    st.error(f"Server {status.name} not found")
        
        with col4:
            if st.button("🗑️ Remove", key=f"remove_{status.name}"):
                try:
                    loop = asyncio.get_event_loop()
                    future = asyncio.run_coroutine_threadsafe(st.session_state.mcp_host.remove_server(status.name), loop)
                    future.result(timeout=10)
                    st.success(f"Removed {status.name}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Failed to remove: {e}")
    
    # Show available tools
    st.subheader("🔧 Available Tools")
    all_tools = st.session_state.mcp_host.get_all_tools()
    
    if not all_tools:
        st.info("No tools available. Make sure servers are connected!")
        
        # Debug info
        with st.expander("🐛 Debug Info"):
            st.write("Server details:")
            for status in server_statuses:
                st.write(f"- {status.name}: connected={status.connected}, tools={len(status.tools)}")
        return
    
    for server_name, tool in all_tools:
        # Handle real MCP Tool objects
        tool_name = tool.name
        tool_description = tool.description
        
        with st.expander(f"🔧 {tool_name} (from {server_name})"):
            st.write(f"**Description:** {tool_description}")
            
            # Show input schema if available
            if hasattr(tool, 'inputSchema') and tool.inputSchema:
                st.write("**Input Schema:**")
                st.json(tool.inputSchema)
            
            # Manual tool execution form
            with st.form(f"execute_{server_name}_{tool_name}"):
                st.write("**Test Tool:**")
                args_input = st.text_area("Arguments (JSON)", value="{}", key=f"args_{server_name}_{tool_name}")
                
                if st.form_submit_button("Execute"):
                    try:
                        args = json.loads(args_input)
                        loop = asyncio.get_event_loop()
                        future = asyncio.run_coroutine_threadsafe(st.session_state.mcp_host.call_tool(server_name, tool_name, args), loop)
                        result = future.result(timeout=30)
                        
                        st.success("Tool executed successfully!")
                        if hasattr(result, 'content') and result.content:
                            if isinstance(result.content, list):
                                content_parts = []
                                for item in result.content:
                                    if hasattr(item, 'text'):
                                        content_parts.append(item.text)
                                    else:
                                        content_parts.append(str(item))
                                content_text = '\n'.join(content_parts)
                            else:
                                content_text = str(result.content)
                            st.code(content_text)
                        else:
                            st.write("No content returned")
                            
                    except Exception as e:
                        st.error(f"Error executing tool: {str(e)}")
