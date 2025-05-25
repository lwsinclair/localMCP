"""
Simple MCP Client - A more robust implementation that avoids TaskGroup issues
"""

import asyncio
import json
import logging
import subprocess
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

@dataclass
class MCPTool:
    name: str
    description: str = ""
    input_schema: Dict[str, Any] = field(default_factory=dict)

@dataclass
class MCPServerStatus:
    name: str
    connected: bool = False
    error: Optional[str] = None
    tools: List[MCPTool] = field(default_factory=list)
    last_updated: float = field(default_factory=time.time)

class SimpleMCPServer:
    """A simpler MCP server implementation that avoids the anyio/TaskGroup issues"""
    
    def __init__(self, name: str, command: str, args: List[str]):
        self.name = name
        self.command = command
        self.args = args
        self.connected = False
        self.tools = []
        self.resources = []  # Add missing resources attribute
        self.prompts = []    # Add missing prompts attribute
        self.process = None
        self._request_id = 0
        
    def _next_request_id(self) -> int:
        self._request_id += 1
        return self._request_id
    
    async def connect(self) -> bool:
        """Connect using a simple subprocess approach"""
        try:
            logger.info(f"Starting MCP server: {self.command} {' '.join(self.args)}")
            
            # Start the process
            self.process = await asyncio.create_subprocess_exec(
                self.command,
                *self.args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            # Wait a moment for the server to start
            await asyncio.sleep(1)
            
            # Check if process is still running
            if self.process.returncode is not None:
                logger.error(f"MCP server process exited with code {self.process.returncode}")
                stderr = await self.process.stderr.read()
                logger.error(f"Server stderr: {stderr.decode()}")
                return False
            
            # Try to initialize
            if await self._initialize():
                self.connected = True
                await self._discover_capabilities()
                logger.info(f"Successfully connected to {self.name} with {len(self.tools)} tools")
                return True
            else:
                logger.error(f"Failed to initialize {self.name}")
                await self.disconnect()
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to {self.name}: {e}")
            await self.disconnect()
            return False
    
    async def _discover_capabilities(self):
        """Discover tools, resources, and prompts"""
        await self._discover_tools()
        await self._discover_resources()
        await self._discover_prompts()
    
    async def _send_request(self, method: str, params: Optional[Dict] = None) -> Optional[Dict]:
        """Send a JSON-RPC request"""
        if not self.process or self.process.stdin is None:
            return None
            
        request_id = self._next_request_id()
        request = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }
        
        try:
            # Send request
            request_json = json.dumps(request) + "\n"
            self.process.stdin.write(request_json.encode())
            await self.process.stdin.drain()
            
            # Read response with timeout
            response_line = await asyncio.wait_for(
                self.process.stdout.readline(), 
                timeout=5.0
            )
            
            if not response_line:
                logger.error(f"No response from {self.name}")
                return None
                
            response = json.loads(response_line.decode().strip())
            
            if "error" in response:
                logger.error(f"RPC error in {self.name}: {response['error']}")
                return None
                
            return response.get("result")
            
        except asyncio.TimeoutError:
            logger.error(f"Request timeout for {self.name}.{method}")
            return None
        except Exception as e:
            logger.error(f"Request failed for {self.name}.{method}: {e}")
            return None
    
    async def _initialize(self) -> bool:
        """Initialize the MCP session"""
        result = await self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {},
                "resources": {},
                "prompts": {}
            },
            "clientInfo": {
                "name": "simple-mcp-client",
                "version": "1.0.0"
            }
        })
        
        if result:
            # Send initialized notification
            notification = {
                "jsonrpc": "2.0",
                "method": "notifications/initialized"
            }
            notification_json = json.dumps(notification) + "\n"
            self.process.stdin.write(notification_json.encode())
            await self.process.stdin.drain()
            return True
        
        return False
    
    async def _discover_tools(self):
        """Discover available tools"""
        result = await self._send_request("tools/list")
        logger.info(f"Tools discovery result for {self.name}: {result}")
        
        if result and "tools" in result:
            self.tools = []
            for tool_data in result["tools"]:
                tool = MCPTool(
                    name=tool_data["name"],
                    description=tool_data.get("description", ""),
                    input_schema=tool_data.get("inputSchema", {})
                )
                self.tools.append(tool)
                logger.info(f"Discovered tool: {tool.name} - {tool.description}")
            logger.info(f"Total tools discovered for {self.name}: {len(self.tools)}")
        else:
            logger.warning(f"No tools found in result for {self.name}: {result}")
            self.tools = []

    async def _discover_resources(self):
        """Discover available resources"""
        result = await self._send_request("resources/list")
        logger.info(f"Resources discovery result for {self.name}: {result}")
        
        if result and "resources" in result:
            self.resources = []
            for resource_data in result["resources"]:
                # Simple resource object (you might want to create a proper class)
                resource = {
                    "name": resource_data["name"],
                    "description": resource_data.get("description", ""),
                    "uri": resource_data.get("uri", "")
                }
                self.resources.append(resource)
                logger.info(f"Discovered resource: {resource['name']} - {resource['description']}")
            logger.info(f"Total resources discovered for {self.name}: {len(self.resources)}")
        else:
            logger.warning(f"No resources found in result for {self.name}: {result}")
            self.resources = []
    
    async def _discover_prompts(self):
        """Discover available prompts"""
        result = await self._send_request("prompts/list")
        logger.info(f"Prompts discovery result for {self.name}: {result}")
        
        if result and "prompts" in result:
            self.prompts = []
            for prompt_data in result["prompts"]:
                # Simple prompt object (you might want to create a proper class)
                prompt = {
                    "name": prompt_data["name"],
                    "description": prompt_data.get("description", ""),
                    "arguments": prompt_data.get("arguments", [])
                }
                self.prompts.append(prompt)
                logger.info(f"Discovered prompt: {prompt['name']} - {prompt['description']}")
            logger.info(f"Total prompts discovered for {self.name}: {len(self.prompts)}")
        else:
            logger.warning(f"No prompts found in result for {self.name}: {result}")
            self.prompts = []
        """Discover available tools"""
        result = await self._send_request("tools/list")
        logger.info(f"Tools discovery result for {self.name}: {result}")
        
        if result and "tools" in result:
            self.tools = []
            for tool_data in result["tools"]:
                tool = MCPTool(
                    name=tool_data["name"],
                    description=tool_data.get("description", ""),
                    input_schema=tool_data.get("inputSchema", {})
                )
                self.tools.append(tool)
                logger.info(f"Discovered tool: {tool.name} - {tool.description}")
            logger.info(f"Total tools discovered for {self.name}: {len(self.tools)}")
        else:
            logger.warning(f"No tools found in result for {self.name}: {result}")
            self.tools = []
    
    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict:
        """Call a tool and return result in expected format"""
        logger.info(f"Attempting to call tool {tool_name} with arguments {arguments}")
        
        # Debug: Log the exact request being sent
        request_data = {
            "name": tool_name,
            "arguments": arguments
        }
        logger.info(f"Sending MCP request: {json.dumps(request_data, indent=2)}")
        
        result = await self._send_request("tools/call", request_data)
        
        logger.info(f"Tool call result for {tool_name}: {result}")
        
        if result:
            # Return result in the format expected by the rest of the system
            return {
                "content": result.get("content", []),
                "isError": False
            }
        else:
            error_msg = f"Tool call failed for {tool_name}"
            logger.error(error_msg)
            return {
                "content": [{"type": "text", "text": error_msg}],
                "isError": True
            }
    
    async def disconnect(self):
        """Disconnect from the server"""
        self.connected = False
        if self.process:
            try:
                self.process.terminate()
                await asyncio.wait_for(self.process.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                self.process.kill()
                await self.process.wait()
            except:
                pass
            self.process = None
        logger.info(f"Disconnected from {self.name}")
    
    def get_status(self) -> MCPServerStatus:
        """Get server status"""
        return MCPServerStatus(
            name=self.name,
            connected=self.connected,
            tools=self.tools,
            last_updated=time.time()
        )

class SimpleMCPHost:
    """Simple MCP Host using the more robust server implementation"""
    
    def __init__(self, config_path: str = "config/servers.json"):
        self.config_path = config_path
        self.servers: Dict[str, SimpleMCPServer] = {}
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
                if server_config["type"] == "stdio":
                    server = SimpleMCPServer(
                        name=name,
                        command=server_config["command"],
                        args=server_config.get("args", [])
                    )
                    self.servers[name] = server
                    logger.info(f"Loaded server config: {name}")
                else:
                    logger.warning(f"Unsupported server type: {server_config['type']} for {name}")
                    
        except Exception as e:
            logger.error(f"Failed to load config from {self.config_path}: {e}")

    async def start(self):
        """Start the MCP host"""
        if self.running:
            logger.info("Simple MCP Host already running")
            return
            
        self.running = True
        logger.info("Starting Simple MCP Host...")
        
        # Connect to all servers
        for server in self.servers.values():
            try:
                await server.connect()
            except Exception as e:
                logger.error(f"Failed to connect to {server.name}: {e}")

    async def stop(self):
        """Stop the MCP host"""
        self.running = False
        for server in self.servers.values():
            await server.disconnect()

    def get_server_statuses(self) -> List[MCPServerStatus]:
        """Get all server statuses"""
        return [server.get_status() for server in self.servers.values()]

    async def call_tool(self, server_name: str, tool_name: str, arguments: Dict[str, Any]) -> Dict:
        """Call a tool and return result in expected format"""
        if server_name not in self.servers:
            raise ValueError(f"Server {server_name} not found")
        return await self.servers[server_name].call_tool(tool_name, arguments)
