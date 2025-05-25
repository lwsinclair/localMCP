"""
Universal MCP Host - Real MCP Implementation
"""

import asyncio
import json
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.client.sse import sse_client
from mcp.types import (
    CallToolResult,
    GetPromptResult,
    ReadResourceResult,
    Tool,
    Prompt,
    Resource
)

logger = logging.getLogger(__name__)

class ServerType(Enum):
    STDIO = "stdio"
    SSE = "sse"
    HTTP = "http"

@dataclass
class MCPServerConfig:
    name: str
    type: ServerType
    command: Optional[str] = None
    args: Optional[List[str]] = None
    env: Optional[Dict[str, str]] = None
    url: Optional[str] = None
    headers: Optional[Dict[str, str]] = None
    description: Optional[str] = None

@dataclass 
class MCPServerStatus:
    name: str
    connected: bool = False
    error: Optional[str] = None
    tools: List[Tool] = field(default_factory=list)
    resources: List[Resource] = field(default_factory=list)
    prompts: List[Prompt] = field(default_factory=list)
    last_updated: float = field(default_factory=time.time)

class RealMCPServer:
    """Real MCP server implementation"""
    
    def __init__(self, config: MCPServerConfig):
        self.config = config
        self.connected = False
        self.tools = []
        self.resources = []
        self.prompts = []
        self._client_task = None
        self._session = None

    async def connect(self) -> bool:
        """Connect to real MCP server"""
        if self.connected:
            return True
            
        logger.info(f"Connecting to {self.config.name} ({self.config.type.value})")
        
        try:
            if self.config.type == ServerType.STDIO:
                return await self._connect_stdio()
            elif self.config.type == ServerType.SSE:
                return await self._connect_sse()
            else:
                logger.error(f"Unsupported server type: {self.config.type}")
                return False
                
        except Exception as e:
            logger.error(f"Connection failed for {self.config.name}: {e}")
            return False

    async def _connect_stdio(self) -> bool:
        """Connect via STDIO with persistent connection"""
        try:
            logger.info(f"Connecting to real MCP server: {self.config.name}")
            
            # Create server parameters
            server_params = StdioServerParameters(
                command=self.config.command,
                args=self.config.args or [],
                env=self.config.env or {}
            )
            
            logger.info(f"Server params: command={self.config.command}, args={self.config.args}")
            
            # Start the client task that will maintain the connection
            self._client_task = asyncio.create_task(self._run_stdio_client(server_params))
            
            # Wait for connection to be established with longer timeout
            logger.info(f"Waiting for connection to {self.config.name}...")
            for i in range(150):  # Wait up to 15 seconds
                await asyncio.sleep(0.1)
                if self.connected:
                    logger.info(f"Connection established after {i * 0.1:.1f} seconds")
                    break
                # Check if the task failed early
                if self._client_task.done():
                    try:
                        await self._client_task
                        # If task completed without setting connected=True, it failed
                        if not self.connected:
                            logger.error(f"Client task completed but connection not established for {self.config.name}")
                            return False
                    except Exception as e:
                        logger.error(f"Client task failed: {e}")
                        return False
                    
            if not self.connected:
                logger.error(f"Connection timeout for {self.config.name} after 15 seconds")
                # Cancel the task if it's still running
                if not self._client_task.done():
                    self._client_task.cancel()
                    try:
                        await self._client_task
                    except asyncio.CancelledError:
                        pass
                return False
                
            logger.info(f"Successfully connected to {self.config.name} with {len(self.tools)} tools")
            return True
                
        except Exception as e:
            logger.error(f"STDIO connection failed for {self.config.name}: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return False
    
    async def _run_stdio_client(self, server_params):
        """Run the STDIO client connection"""
        try:
            async with stdio_client(server_params) as (read_stream, write_stream):
                logger.info(f"STDIO connection established for {self.config.name}")
                
                try:
                    # Create client session
                    session = ClientSession(read_stream, write_stream)
                    
                    # Initialize session with shorter timeout and better error handling
                    logger.info(f"Initializing session for {self.config.name}")
                    
                    # Try to initialize the session
                    async def init_with_retry():
                        for attempt in range(3):
                            try:
                                await asyncio.wait_for(session.initialize(), timeout=3.0)
                                return True
                            except asyncio.TimeoutError:
                                logger.warning(f"Session init attempt {attempt + 1} timed out for {self.config.name}")
                                if attempt < 2:
                                    await asyncio.sleep(0.5)
                                else:
                                    raise
                            except Exception as e:
                                logger.error(f"Session init attempt {attempt + 1} failed for {self.config.name}: {e}")
                                if attempt < 2:
                                    await asyncio.sleep(0.5)
                                else:
                                    raise
                        return False
                    
                    success = await init_with_retry()
                    if not success:
                        logger.error(f"Failed to initialize session for {self.config.name} after 3 attempts")
                        return
                    
                    logger.info(f"Session initialized for {self.config.name}")
                    
                    # Small delay to ensure session is fully ready
                    await asyncio.sleep(0.2)
                    
                    self._session = session
                    self.connected = True  # Set connected before capability discovery
                    
                    # Get server capabilities with timeout protection
                    try:
                        logger.info(f"Listing tools for {self.config.name}")
                        result = await asyncio.wait_for(session.list_tools(), timeout=5.0)
                        self.tools = result.tools if result else []
                        logger.info(f"Loaded {len(self.tools)} tools from {self.config.name}")
                    except asyncio.TimeoutError:
                        logger.warning(f"Tool listing timeout for {self.config.name}")
                        self.tools = []
                    except Exception as e:
                        logger.warning(f"Tool listing failed for {self.config.name}: {e}")
                        self.tools = []
                    
                    try:
                        logger.info(f"Listing resources for {self.config.name}")
                        result = await asyncio.wait_for(session.list_resources(), timeout=5.0)
                        self.resources = result.resources if result else []
                        logger.info(f"Loaded {len(self.resources)} resources from {self.config.name}")
                    except asyncio.TimeoutError:
                        logger.warning(f"Resource listing timeout for {self.config.name}")
                        self.resources = []
                    except Exception as e:
                        logger.warning(f"Resource listing failed for {self.config.name}: {e}")
                        self.resources = []
                    
                    try:
                        logger.info(f"Listing prompts for {self.config.name}")
                        result = await asyncio.wait_for(session.list_prompts(), timeout=5.0)
                        self.prompts = result.prompts if result else []
                        logger.info(f"Loaded {len(self.prompts)} prompts from {self.config.name}")
                    except asyncio.TimeoutError:
                        logger.warning(f"Prompt listing timeout for {self.config.name}")
                        self.prompts = []
                    except Exception as e:
                        logger.warning(f"Prompt listing failed for {self.config.name}: {e}")
                        self.prompts = []
                    
                    logger.info(f"MCP client connected successfully for {self.config.name} with {len(self.tools)} tools, {len(self.resources)} resources, {len(self.prompts)} prompts")
                    
                    # Keep the connection alive until disconnected
                    try:
                        while self.connected:
                            await asyncio.sleep(1)
                    except asyncio.CancelledError:
                        logger.info(f"Connection cancelled for {self.config.name}")
                        raise
                        
                except Exception as e:
                    logger.error(f"Session handling failed for {self.config.name}: {e}")
                    import traceback
                    logger.error(f"Full traceback: {traceback.format_exc()}")
                    self.connected = False
                    self._session = None
                    raise
                    
        except Exception as e:
            logger.error(f"STDIO client error for {self.config.name}: {e}")
            import traceback
            logger.error(f"Full traceback: {traceback.format_exc()}")
            self.connected = False
            self._session = None
            raise

    async def _connect_sse(self) -> bool:
        """Connect via SSE"""
        try:
            logger.info(f"Connecting to SSE: {self.config.url}")
            
            # Start SSE connection in background
            self._client_task = asyncio.create_task(self._run_sse_client())
            
            # Wait for connection
            for _ in range(10):
                await asyncio.sleep(0.5)
                if self.connected:
                    break
                    
            return self.connected
                
        except Exception as e:
            logger.error(f"SSE connection failed for {self.config.name}: {e}")
            return False

    async def _run_sse_client(self):
        """Run the SSE client connection"""
        try:
            async with sse_client(self.config.url, headers=self.config.headers or {}) as (read_stream, write_stream):
                logger.info(f"SSE connection established for {self.config.name}")
                
                session = ClientSession(read_stream, write_stream)
                await session.initialize()
                
                self._session = session
                await self._discover_capabilities()
                
                self.connected = True
                logger.info(f"SSE connection successful for {self.config.name}")
                
                # Keep connection alive
                try:
                    while self.connected:
                        await asyncio.sleep(1)
                except asyncio.CancelledError:
                    logger.info(f"SSE connection cancelled for {self.config.name}")
                    
        except Exception as e:
            logger.error(f"SSE client error for {self.config.name}: {e}")
        finally:
            self.connected = False
            self._session = None

    async def _discover_capabilities(self):
        """Discover server capabilities with timeout protection"""
        if not self._session:
            return
            
        try:
            logger.debug(f"Discovering capabilities for {self.config.name}")
            
            # List tools with timeout
            tools_result = await asyncio.wait_for(
                self._session.list_tools(), 
                timeout=5.0
            )
            self.tools = tools_result.tools if tools_result else []

            # List resources with timeout
            resources_result = await asyncio.wait_for(
                self._session.list_resources(), 
                timeout=5.0
            )
            self.resources = resources_result.resources if resources_result else []

            # List prompts with timeout
            prompts_result = await asyncio.wait_for(
                self._session.list_prompts(), 
                timeout=5.0
            )
            self.prompts = prompts_result.prompts if prompts_result else []

            logger.info(f"Discovered {len(self.tools)} tools, {len(self.resources)} resources, {len(self.prompts)} prompts for {self.config.name}")
            
        except asyncio.TimeoutError as e:
            logger.error(f"Capability discovery timeout for {self.config.name}: {e}")
            # Set empty capabilities but don't fail the connection
            self.tools = []
            self.resources = []
            self.prompts = []
        except Exception as e:
            logger.error(f"Capability discovery failed for {self.config.name}: {e}")
            # Set empty capabilities but don't fail the connection
            self.tools = []
            self.resources = []
            self.prompts = []

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """Call a tool using the real MCP session"""
        if not self.connected or not self._session:
            raise RuntimeError(f"Server {self.config.name} not connected")
        
        logger.info(f"Calling tool {name} on {self.config.name} with args {arguments}")
        
        try:
            result = await self._session.call_tool(name, arguments)
            logger.info(f"Tool {name} completed successfully")
            return result
        except Exception as e:
            logger.error(f"Tool call failed for {name}: {e}")
            raise

    async def read_resource(self, uri: str) -> ReadResourceResult:
        """Read a resource"""
        if not self._session or not self.connected:
            raise RuntimeError(f"Server {self.config.name} not connected")
        return await self._session.read_resource(uri)

    async def get_prompt(self, name: str, arguments: Optional[Dict[str, str]] = None) -> GetPromptResult:
        """Get a prompt"""
        if not self._session or not self.connected:
            raise RuntimeError(f"Server {self.config.name} not connected")
        return await self._session.get_prompt(name, arguments or {})

    async def disconnect(self):
        """Disconnect"""
        self.connected = False
        
        if self._client_task:
            self._client_task.cancel()
            try:
                await self._client_task
            except asyncio.CancelledError:
                pass
            
        self._session = None
        logger.info(f"Disconnected from {self.config.name}")

    def get_status(self) -> MCPServerStatus:
        """Get status"""
        return MCPServerStatus(
            name=self.config.name,
            connected=self.connected,
            tools=self.tools,
            resources=self.resources,
            prompts=self.prompts,
            last_updated=time.time()
        )

class UniversalMCPHost:
    """Real MCP Host implementation"""
    
    def __init__(self, config_path: str = "config/servers.json"):
        self.config_path = config_path
        self.servers: Dict[str, RealMCPServer] = {}
        self.running = False
        self._load_config()
    
    def _load_config(self):
        """Load server configurations"""
        try:
            config_file = Path(self.config_path)
            if not config_file.exists():
                logger.warning(f"Config file not found: {self.config_path}")
                return
                
            with open(config_file, 'r') as f:
                config_data = json.load(f)
            
            self.servers.clear()
            for name, server_config in config_data.get("servers", {}).items():
                try:
                    mcp_config = MCPServerConfig(
                        name=name,
                        type=ServerType(server_config["type"]),
                        command=server_config.get("command"),
                        args=server_config.get("args", []),
                        env=server_config.get("env"),
                        url=server_config.get("url"),
                        headers=server_config.get("headers"),
                        description=server_config.get("description")
                    )
                    self.servers[name] = RealMCPServer(mcp_config)
                    logger.info(f"Loaded server config: {name}")
                except Exception as e:
                    logger.error(f"Failed to load server config {name}: {e}")
                    
        except Exception as e:
            logger.error(f"Failed to load config from {self.config_path}: {e}")

    async def start(self):
        """Start the MCP host"""
        if self.running:
            logger.info("MCP Host already running")
            return
            
        self.running = True
        logger.info("Starting Universal MCP Host...")
        
        # Connect to all servers
        connection_tasks = []
        for server in self.servers.values():
            connection_tasks.append(server.connect())
        
        if connection_tasks:
            results = await asyncio.gather(*connection_tasks, return_exceptions=True)
            for i, result in enumerate(results):
                server_name = list(self.servers.keys())[i]
                if isinstance(result, Exception):
                    logger.error(f"Failed to connect to {server_name}: {result}")
                elif result:
                    logger.info(f"Successfully connected to {server_name}")
                else:
                    logger.warning(f"Connection to {server_name} returned False")

    async def stop(self):
        """Stop the MCP host"""
        self.running = False
        for server in self.servers.values():
            await server.disconnect()

    def get_all_tools(self) -> List[tuple[str, Tool]]:
        """Get all tools"""
        all_tools = []
        for server_name, server in self.servers.items():
            if server.connected:
                for tool in server.tools:
                    all_tools.append((server_name, tool))
        return all_tools

    def get_all_resources(self) -> List[tuple[str, Resource]]:
        """Get all resources"""
        all_resources = []
        for server_name, server in self.servers.items():
            if server.connected:
                for resource in server.resources:
                    all_resources.append((server_name, resource))
        return all_resources

    def get_all_prompts(self) -> List[tuple[str, Prompt]]:
        """Get all prompts"""
        all_prompts = []
        for server_name, server in self.servers.items():
            if server.connected:
                for prompt in server.prompts:
                    all_prompts.append((server_name, prompt))
        return all_prompts

    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> CallToolResult:
        """Call a tool"""
        if server_name not in self.servers:
            raise ValueError(f"Server {server_name} not found")
        return await self.servers[server_name].call_tool(tool_name, arguments)

    async def read_resource(self, server_name: str, uri: str) -> ReadResourceResult:
        """Read a resource"""
        if server_name not in self.servers:
            raise ValueError(f"Server {server_name} not found")
        return await self.servers[server_name].read_resource(uri)

    async def get_prompt(self, server_name: str, prompt_name: str, arguments: Optional[Dict[str, str]] = None) -> GetPromptResult:
        """Get a prompt"""
        if server_name not in self.servers:
            raise ValueError(f"Server {server_name} not found")
        return await self.servers[server_name].get_prompt(prompt_name, arguments)

    def get_server_statuses(self) -> List[MCPServerStatus]:
        """Get all server statuses"""
        return [server.get_status() for server in self.servers.values()]

    async def add_server(self, config: MCPServerConfig) -> bool:
        """Add a new server"""
        if config.name in self.servers:
            return False
        
        server = RealMCPServer(config)
        success = await server.connect()
        
        if success:
            self.servers[config.name] = server
        
        return success

    async def remove_server(self, name: str) -> bool:
        """Remove a server"""
        if name not in self.servers:
            return False
        
        await self.servers[name].disconnect()
        del self.servers[name]
        return True

    def reload_config(self):
        """Reload configuration"""
        self._load_config()
