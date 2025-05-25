import React, { useState, useEffect, useCallback } from 'react';
import axios from 'axios';
import { 
  Server, 
  MessageCircle,
  Settings, 
  Wrench, 
  Play, 
  Square, 
  RefreshCw,
  Plus,
  CheckCircle,
  XCircle,
  Clock
} from 'lucide-react';
import MCPToolsEnhanced from './MCPTools';
import ChatInterface from './ChatInterface';
import AddServerModal from './AddServerModal';

const API_BASE = 'http://localhost:8000';

function App() {
  const [servers, setServers] = useState([]);
  const [isLoading, setIsLoading] = useState(true);
  const [activeTab, setActiveTab] = useState('chat');
  
  // Global state for chat and model selection
  const [messages, setMessages] = useState([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [showAddServerModal, setShowAddServerModal] = useState(false);

  const loadServers = useCallback(async () => {
    try {
      console.log('Loading servers from:', `${API_BASE}/api/servers`);
      setIsLoading(true);
      const response = await axios.get(`${API_BASE}/api/servers`);
      console.log('Servers loaded:', response.data);
      setServers(response.data);
    } catch (error) {
      console.error('Failed to load servers:', error);
      console.error('Error details:', {
        message: error.message,
        code: error.code,
        response: error.response?.data,
        status: error.response?.status
      });
      // Show user-friendly error
      if (error.code === 'ERR_NETWORK') {
        console.log('Backend not running. Make sure FastAPI server is started.');
        setServers([]); // Show empty state
      }
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    console.log('App mounted, loading servers...');
    loadServers();
  }, [loadServers]);

  // Separate useEffect for auto-refresh with longer interval and smarter refresh
  useEffect(() => {
    const interval = setInterval(() => {
      // Only refresh servers if we're not in the chat tab
      if (activeTab !== 'chat') {
        loadServers();
      }
    }, 15000); // Increased to 15 seconds to reduce interruptions
    return () => clearInterval(interval);
  }, [activeTab, loadServers]);

  const connectServer = async (serverName) => {
    // Optimistically update UI
    setServers(prev => prev.map(s => 
      s.name === serverName ? { ...s, status: 'connecting' } : s
    ));

    try {
      const response = await axios.post(`${API_BASE}/api/servers/${serverName}/connect`);
      // Success (200 status) - refresh server list
      setTimeout(loadServers, 1000);
    } catch (error) {
      console.error(`Failed to connect to ${serverName}:`, error);
      
      // Revert optimistic update
      setServers(prev => prev.map(s => 
        s.name === serverName ? { ...s, status: 'disconnected' } : s
      ));
      
      // Show user-friendly error message
      const errorMessage = error.response?.data?.detail || error.message;
      alert(`Failed to connect to ${serverName}: ${errorMessage}`);
    }
  };

  const disconnectServer = async (serverName) => {
    try {
      await axios.post(`${API_BASE}/api/servers/${serverName}/disconnect`);
      await loadServers();
    } catch (error) {
      console.error(`Failed to disconnect from ${serverName}:`, error);
      const errorMessage = error.response?.data?.detail || error.message;
      alert(`Failed to disconnect from ${serverName}: ${errorMessage}`);
    }
  };

  const addServer = async (serverConfig) => {
    try {
      const response = await axios.post(`${API_BASE}/api/servers/add`, serverConfig);
      setShowAddServerModal(false);
      await loadServers();
      alert(`Server '${serverConfig.name}' added successfully!`);
    } catch (error) {
      console.error('Failed to add server:', error);
      const errorMessage = error.response?.data?.detail || error.message;
      alert(`Failed to add server: ${errorMessage}`);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'connected':
        return <CheckCircle className="w-5 h-5 text-green-500" />;
      case 'connecting':
        return <Clock className="w-5 h-5 text-yellow-500 animate-spin" />;
      case 'disconnected':
        return <XCircle className="w-5 h-5 text-red-500" />;
      default:
        return <XCircle className="w-5 h-5 text-gray-400" />;
    }
  };

  const connectedServers = servers.filter(s => s.status === 'connected');  const ServerCard = ({ server }) => (
    <div className="bg-white rounded-lg shadow-md p-6 border border-gray-200 hover:shadow-lg transition-shadow">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center space-x-3">
          {getStatusIcon(server.status)}
          <h3 className="text-lg font-semibold text-gray-800">{server.name}</h3>
        </div>
        <div className="flex items-center space-x-2">
          {server.status === 'connected' ? (
            <button
              onClick={() => disconnectServer(server.name)}
              className="px-3 py-1 bg-red-500 text-white rounded-md hover:bg-red-600 transition-colors flex items-center"
            >
              <Square className="w-4 h-4 mr-1" />
              Stop
            </button>
          ) : (
            <button
              onClick={() => connectServer(server.name)}
              className="px-3 py-1 bg-green-500 text-white rounded-md hover:bg-green-600 transition-colors flex items-center"
              disabled={server.status === 'connecting'}
            >
              {server.status === 'connecting' ? (
                <RefreshCw className="w-4 h-4 mr-1 animate-spin" />
              ) : (
                <Play className="w-4 h-4 mr-1" />
              )}
              {server.status === 'connecting' ? 'Connecting...' : 'Connect'}
            </button>
          )}
        </div>
      </div>
      
      <div className="text-sm text-gray-600 space-y-2">
        <div className="flex justify-between">
          <span className="font-medium">Protocol:</span>
          <span className="text-gray-800">{server.protocol}</span>
        </div>
        <div className="flex justify-between">
          <span className="font-medium">Command:</span>
          <span className="text-gray-800 text-xs font-mono">{server.command}</span>
        </div>
        
        {server.status === 'connected' && (
          <div className="mt-3 pt-3 border-t border-gray-200">
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div className="text-center p-2 bg-blue-50 rounded">
                <div className="font-bold text-blue-600">{server.tools_count || 0}</div>
                <div className="text-blue-700">Tools</div>
              </div>
              <div className="text-center p-2 bg-green-50 rounded">
                <div className="font-bold text-green-600">{server.resources_count || 0}</div>
                <div className="text-green-700">Resources</div>
              </div>
              <div className="text-center p-2 bg-purple-50 rounded">
                <div className="font-bold text-purple-600">{server.prompts_count || 0}</div>
                <div className="text-purple-700">Prompts</div>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );

  const ServerManagement = () => (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h2 className="text-xl font-semibold flex items-center">
          <Settings className="w-5 h-5 mr-2" />
          Server Management
        </h2>
        <div className="flex items-center space-x-2">
          <button
            onClick={loadServers}
            className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600 transition-colors flex items-center"
          >
            <RefreshCw className="w-4 h-4 mr-2" />
            Refresh
          </button>
          <button className="px-4 py-2 bg-green-500 text-white rounded-md hover:bg-green-600 transition-colors flex items-center"
                  onClick={() => setShowAddServerModal(true)}>
            <Plus className="w-4 h-4 mr-2" />
            Add Server
          </button>
        </div>
      </div>

      {isLoading ? (
        <div className="flex items-center justify-center py-12">
          <RefreshCw className="w-8 h-8 animate-spin text-blue-500" />
          <span className="ml-2 text-gray-600">Loading servers...</span>
        </div>
      ) : servers.length === 0 ? (
        <div className="text-center py-12 text-gray-500">
          <Server className="w-16 h-16 mx-auto mb-4 text-gray-300" />
          <p className="text-lg font-medium">No MCP servers configured</p>
          <p className="text-sm mt-2">Add servers to the configuration to get started.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {servers.map(server => (
            <ServerCard key={server.name} server={server} />
          ))}
        </div>
      )}

      {/* Connection Status Summary */}
      <div className="bg-white rounded-lg shadow-md p-6">
        <h3 className="text-lg font-semibold mb-4">Connection Summary</h3>
        <div className="grid grid-cols-3 gap-4 text-center">
          <div className="p-4 bg-green-50 rounded-lg border border-green-200">
            <div className="text-3xl font-bold text-green-600">
              {servers.filter(s => s.status === 'connected').length}
            </div>
            <div className="text-sm text-green-700 font-medium">Connected</div>
            <div className="text-xs text-green-600 mt-1">
              {servers.filter(s => s.status === 'connected').reduce((sum, s) => sum + (s.tools_count || 0), 0)} tools available
            </div>
          </div>
          <div className="p-4 bg-yellow-50 rounded-lg border border-yellow-200">
            <div className="text-3xl font-bold text-yellow-600">
              {servers.filter(s => s.status === 'connecting').length}
            </div>
            <div className="text-sm text-yellow-700 font-medium">Connecting</div>
            <div className="text-xs text-yellow-600 mt-1">In progress</div>
          </div>
          <div className="p-4 bg-red-50 rounded-lg border border-red-200">
            <div className="text-3xl font-bold text-red-600">
              {servers.filter(s => s.status === 'disconnected').length}
            </div>
            <div className="text-sm text-red-700 font-medium">Disconnected</div>
            <div className="text-xs text-red-600 mt-1">Not available</div>
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="min-h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center">
              <Server className="w-8 h-8 text-blue-600 mr-3" />
              <div>
                <h1 className="text-xl font-bold text-gray-900">Universal MCP Host</h1>
                <p className="text-xs text-gray-500">React + FastAPI</p>
              </div>
            </div>
            <div className="flex items-center space-x-4">
              <div className="text-sm text-gray-600">
                <span className="font-medium text-green-600">{connectedServers.length}</span> / {servers.length} connected
              </div>
              <div className="w-3 h-3 rounded-full bg-green-500 animate-pulse" title="Backend connected"></div>
            </div>
          </div>
        </div>
      </header>

      {/* Navigation Tabs */}
      <nav className="bg-white border-b border-gray-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex space-x-8">
            {[
              { id: 'chat', label: '💬 Chat', icon: MessageCircle },
              { id: 'servers', label: '🔧 Servers', icon: Settings },
              { id: 'tools', label: '🛠️ Tools', icon: Wrench }
            ].map(tab => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`py-4 px-1 border-b-2 font-medium text-sm transition-colors ${
                  activeTab === tab.id
                    ? 'border-blue-500 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
                }`}
              >
                {tab.label}
              </button>
            ))}
          </div>
        </div>
      </nav>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {activeTab === 'chat' && (
          <ChatInterface 
            connectedServers={connectedServers} 
            messages={messages}
            setMessages={setMessages}
            selectedModel={selectedModel}
            setSelectedModel={setSelectedModel}
          />
        )}
        {activeTab === 'servers' && <ServerManagement />}
        {activeTab === 'tools' && <MCPToolsEnhanced servers={servers} connectedServers={connectedServers} />}
      </main>
      
      {/* Add Server Modal */}
      <AddServerModal
        isOpen={showAddServerModal}
        onClose={() => setShowAddServerModal(false)}
        onAdd={addServer}
      />
    </div>
  );
}

export default App;