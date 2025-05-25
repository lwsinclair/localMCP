import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { 
  Wrench, 
  Play, 
  RefreshCw,
  CheckCircle,
  XCircle
} from 'lucide-react';

const API_BASE = 'http://localhost:8000';

// Enhanced MCP Tools component with dynamic tool loading
const MCPToolsEnhanced = ({ servers, connectedServers }) => {
  const [selectedServer, setSelectedServer] = useState('');
  const [selectedTool, setSelectedTool] = useState('');
  const [toolArgs, setToolArgs] = useState('{}');
  const [toolResult, setToolResult] = useState(null);
  const [isExecuting, setIsExecuting] = useState(false);
  const [availableTools, setAvailableTools] = useState([]);
  const [allTools, setAllTools] = useState([]);
  const [loadingTools, setLoadingTools] = useState(false);
  const [activeSubTab, setActiveSubTab] = useState('browse');

  // Load all tools from all connected servers
  useEffect(() => {
    const loadAllTools = async () => {
      if (connectedServers.length === 0) return;
      
      setLoadingTools(true);
      const allToolsData = [];
      
      for (const server of connectedServers) {
        try {
          const response = await axios.get(`${API_BASE}/api/servers/${server.name}/tools`);
          const serverTools = response.data.tools || [];
          serverTools.forEach(tool => {
            allToolsData.push({
              ...tool,
              serverName: server.name,
              fullName: `${server.name}.${tool.name}`
            });
          });
        } catch (error) {
          console.error(`Failed to load tools for ${server.name}:`, error);
        }
      }
      
      setAllTools(allToolsData);
      setLoadingTools(false);
    };
    
    loadAllTools();
  }, [connectedServers]);

  // Load tools when server is selected
  useEffect(() => {
    if (selectedServer) {
      loadServerTools(selectedServer);
    }
  }, [selectedServer]);

  const loadServerTools = async (serverName) => {
    try {
      setLoadingTools(true);
      const response = await axios.get(`${API_BASE}/api/servers/${serverName}/tools`);
      setAvailableTools(response.data.tools || []);
    } catch (error) {
      console.error('Failed to load tools:', error);
      setAvailableTools([]);
    } finally {
      setLoadingTools(false);
    }
  };

  const executeTool = async () => {
    if (!selectedServer || !selectedTool) return;

    setIsExecuting(true);
    try {
      const args = JSON.parse(toolArgs);
      const response = await axios.post(`${API_BASE}/api/servers/${selectedServer}/tools/${selectedTool}`, {
        arguments: args
      });
      setToolResult(response.data);
    } catch (error) {
      console.error('Tool execution failed:', error);
      const errorMessage = error.response?.data?.detail || error.message;
      setToolResult({
        error: errorMessage
      });
    } finally {
      setIsExecuting(false);
    }
  };

  return (
    <div className="space-y-6">
      {/* Sub-navigation tabs */}
      <div className="bg-white rounded-lg shadow-md">
        <div className="border-b border-gray-200">
          <nav className="flex space-x-8 px-6">
            {[
              { id: 'browse', label: '📖 Browse Tools', icon: Wrench },
              { id: 'execute', label: '▶️ Execute Tools', icon: Play }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveSubTab(tab.id)}
                className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeSubTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </nav>
        </div>
      </div>

      {activeSubTab === 'browse' && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold flex items-center">
              <Wrench className="w-5 h-5 mr-2" />
              All Available Tools ({allTools.length})
            </h2>
            {loadingTools && (
              <RefreshCw className="w-4 h-4 animate-spin text-gray-400" />
            )}
          </div>

          {connectedServers.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Wrench className="w-16 h-16 mx-auto mb-4 text-gray-300" />
              <p>No connected servers available.</p>
              <p className="text-sm mt-2">Connect to MCP servers in the Server Management tab first.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {allTools.map((tool, index) => (
                <div key={`${tool.serverName}-${tool.name}-${index}`} className="border border-gray-200 rounded-lg p-4 hover:border-blue-300 transition-colors">
                  <div className="flex items-start justify-between">
                    <div className="flex-1">
                      <div className="flex items-center space-x-2 mb-2">
                        <h3 className="font-medium text-lg text-gray-900">{tool.fullName}</h3>
                        <span className="px-2 py-1 bg-blue-100 text-blue-800 text-xs rounded-full">
                          {tool.serverName}
                        </span>
                      </div>
                      <p className="text-gray-600 mb-3">{tool.description}</p>
                      
                      {/* Tool schema information */}
                      {tool.inputSchema && tool.inputSchema.properties && (
                        <div className="bg-gray-50 rounded-md p-3">
                          <h4 className="text-sm font-medium text-gray-700 mb-2">Parameters:</h4>
                          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-2">
                            {Object.entries(tool.inputSchema.properties).map(([param, details]) => (
                              <div key={param} className="text-xs">
                                <span className="font-mono font-medium text-blue-600">{param}</span>
                                <span className="text-gray-500"> ({details.type})</span>
                                {tool.inputSchema.required && tool.inputSchema.required.includes(param) && (
                                  <span className="text-red-500 ml-1">*</span>
                                )}
                                {details.description && (
                                  <div className="text-gray-600 mt-1">{details.description}</div>
                                )}
                              </div>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>
                    
                    <button
                      onClick={() => {
                        setSelectedServer(tool.serverName);
                        setSelectedTool(tool.name);
                        setActiveSubTab('execute');
                        // Set example args
                        if (tool.name === 'list_directory') {
                          setToolArgs('{"path": "/tmp"}');
                        } else if (tool.name === 'read_file') {
                          setToolArgs('{"path": "/tmp/example.txt"}');
                        } else {
                          setToolArgs('{}');
                        }
                      }}
                      className="ml-4 px-3 py-1 bg-blue-500 text-white text-sm rounded hover:bg-blue-600 transition-colors"
                    >
                      Try It
                    </button>
                  </div>
                </div>
              ))}
              
              {allTools.length === 0 && !loadingTools && (
                <div className="text-center py-8 text-gray-500">
                  <p>No tools discovered yet.</p>
                  <p className="text-sm mt-2">Make sure your servers are properly connected and exposing tools.</p>
                </div>
              )}
            </div>
          )}
        </div>
      )}

      {activeSubTab === 'execute' && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h2 className="text-xl font-semibold mb-4 flex items-center">
            <Play className="w-5 h-5 mr-2" />
            Tool Execution
          </h2>

          {connectedServers.length === 0 ? (
            <div className="text-center py-8 text-gray-500">
              <Wrench className="w-16 h-16 mx-auto mb-4 text-gray-300" />
              <p>No connected servers available.</p>
              <p className="text-sm mt-2">Connect to MCP servers in the Server Management tab first.</p>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Server Selection */}
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Select Server
                </label>
                <select
                  value={selectedServer}
                  onChange={(e) => {
                    setSelectedServer(e.target.value);
                    setSelectedTool('');
                    setToolResult(null);
                  }}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                >
                  <option value="">Choose a server...</option>
                  {connectedServers.map(server => (
                    <option key={server.name} value={server.name}>
                      {server.name} ({server.tools_count} tools)
                    </option>
                  ))}
                </select>
              </div>

              {/* Tool Selection */}
              {selectedServer && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Select Tool
                    {loadingTools && <span className="ml-2 text-xs text-gray-500">Loading...</span>}
                  </label>
                  <select
                    value={selectedTool}
                    onChange={(e) => {
                      setSelectedTool(e.target.value);
                      setToolResult(null);
                      // Set default args based on tool
                      const tool = availableTools.find(t => t.name === e.target.value);
                      if (tool && tool.name === 'list_directory') {
                        setToolArgs('{"path": "/tmp"}');
                      } else if (tool && tool.name === 'read_file') {
                        setToolArgs('{"path": "/tmp/example.txt"}');
                      } else {
                        setToolArgs('{}');
                      }
                    }}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                    disabled={loadingTools}
                  >
                    <option value="">Choose a tool...</option>
                    {availableTools.map(tool => (
                      <option key={tool.name} value={tool.name}>
                        {tool.name} - {tool.description}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* Tool Arguments */}
              {selectedTool && (
                <div>
                  <label className="block text-sm font-medium text-gray-700 mb-2">
                    Arguments (JSON)
                  </label>
                  <textarea
                    value={toolArgs}
                    onChange={(e) => setToolArgs(e.target.value)}
                    rows={4}
                    className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                    placeholder='{"path": "/tmp"}'
                  />
                  <p className="text-xs text-gray-500 mt-1">
                    Provide arguments as valid JSON. Leave empty {} if no arguments needed.
                  </p>
                </div>
              )}

              {/* Execute Button */}
              {selectedTool && (
                <button
                  onClick={executeTool}
                  disabled={isExecuting}
                  className="w-full px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center"
                >
                  {isExecuting ? (
                    <RefreshCw className="w-4 h-4 mr-2 animate-spin" />
                  ) : (
                    <Play className="w-4 h-4 mr-2" />
                  )}
                  {isExecuting ? 'Executing...' : 'Execute Tool'}
                </button>
              )}
            </div>
          )}
        </div>
      )}

      {/* Tool Result */}
      {toolResult && (
        <div className="bg-white rounded-lg shadow-md p-6">
          <h3 className="text-lg font-semibold mb-4">Tool Result</h3>
          {toolResult.error ? (
            <div className="bg-red-50 border border-red-200 rounded-md p-4">
              <div className="flex items-center">
                <XCircle className="w-5 h-5 text-red-500 mr-2" />
                <span className="font-medium text-red-800">Error</span>
              </div>
              <p className="text-red-700 mt-2 font-mono text-sm">{toolResult.error}</p>
            </div>
          ) : (
            <div className="bg-green-50 border border-green-200 rounded-md p-4">
              <div className="flex items-center mb-2">
                <CheckCircle className="w-5 h-5 text-green-500 mr-2" />
                <span className="font-medium text-green-800">Success</span>
              </div>
              <pre className="text-sm text-gray-800 whitespace-pre-wrap overflow-x-auto bg-white p-3 rounded border max-h-96">
                {JSON.stringify(toolResult.result || toolResult, null, 2)}
              </pre>
            </div>
          )}
        </div>
      )}

      {/* Available Tools Summary */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold mb-4">Available Tools Summary</h3>
        <div className="space-y-4">
          {connectedServers.map(server => (
            <div key={server.name} className="border border-gray-200 rounded-lg p-4">
              <div className="flex items-center justify-between mb-2">
                <h4 className="font-medium text-gray-800">{server.name}</h4>
                <span className="text-sm text-gray-500">
                  {server.tools_count} tools, {server.resources_count} resources, {server.prompts_count} prompts
                </span>
              </div>
              <div className="grid grid-cols-3 gap-4 text-sm text-gray-600">
                <div className="bg-blue-50 p-2 rounded">
                  <span className="font-medium text-blue-800">Tools:</span> {server.tools_count}
                </div>
                <div className="bg-green-50 p-2 rounded">
                  <span className="font-medium text-green-800">Resources:</span> {server.resources_count}
                </div>
                <div className="bg-purple-50 p-2 rounded">
                  <span className="font-medium text-purple-800">Prompts:</span> {server.prompts_count}
                </div>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

export default MCPToolsEnhanced;
