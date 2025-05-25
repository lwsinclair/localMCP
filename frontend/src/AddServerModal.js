import React, { useState } from 'react';
import { X, Plus, Server } from 'lucide-react';

const AddServerModal = ({ isOpen, onClose, onAdd }) => {
  const [serverData, setServerData] = useState({
    name: '',
    type: 'stdio',
    command: '',
    args: '',
    url: '',
    headers: '',
    description: ''
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    
    // Parse args and headers
    const args = serverData.args ? serverData.args.split(' ').filter(arg => arg.trim()) : [];
    const headers = serverData.headers ? JSON.parse(serverData.headers) : {};
    
    const newServer = {
      name: serverData.name,
      type: serverData.type,
      description: serverData.description,
      ...(serverData.type === 'stdio' ? {
        command: serverData.command,
        args: args
      } : {
        url: serverData.url,
        headers: headers
      })
    };
    
    onAdd(newServer);
    setServerData({
      name: '',
      type: 'stdio',
      command: '',
      args: '',
      url: '',
      headers: '',
      description: ''
    });
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className="bg-white rounded-lg p-6 w-full max-w-md max-h-[90vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-xl font-semibold flex items-center">
            <Plus className="w-5 h-5 mr-2" />
            Add MCP Server
          </h2>
          <button
            onClick={onClose}
            className="text-gray-400 hover:text-gray-600"
          >
            <X className="w-5 h-5" />
          </button>
        </div>
        
        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Server Name *
            </label>
            <input
              type="text"
              required
              value={serverData.name}
              onChange={(e) => setServerData({...serverData, name: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="e.g., my-filesystem"
            />
          </div>
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Connection Type *
            </label>
            <select
              value={serverData.type}
              onChange={(e) => setServerData({...serverData, type: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
            >
              <option value="stdio">STDIO (Local)</option>
              <option value="sse">HTTP SSE (Remote)</option>
            </select>
          </div>
          
          {serverData.type === 'stdio' ? (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Command *
                </label>
                <input
                  type="text"
                  required
                  value={serverData.command}
                  onChange={(e) => setServerData({...serverData, command: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g., npx, uvx, python"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Arguments
                </label>
                <input
                  type="text"
                  value={serverData.args}
                  onChange={(e) => setServerData({...serverData, args: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g., -y @modelcontextprotocol/server-filesystem /tmp"
                />
                <p className="text-xs text-gray-500 mt-1">Space-separated arguments</p>
              </div>
            </>
          ) : (
            <>
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Server URL *
                </label>
                <input
                  type="url"
                  required
                  value={serverData.url}
                  onChange={(e) => setServerData({...serverData, url: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="e.g., https://api.example.com/mcp"
                />
              </div>
              
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1">
                  Headers (JSON)
                </label>
                <textarea
                  value={serverData.headers}
                  onChange={(e) => setServerData({...serverData, headers: e.target.value})}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 font-mono text-sm"
                  rows={3}
                  placeholder='{"Authorization": "Bearer token"}'
                />
              </div>
            </>
          )}
          
          <div>
            <label className="block text-sm font-medium text-gray-700 mb-1">
              Description
            </label>
            <input
              type="text"
              value={serverData.description}
              onChange={(e) => setServerData({...serverData, description: e.target.value})}
              className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
              placeholder="Brief description of this server"
            />
          </div>
          
          <div className="flex justify-end space-x-3 pt-4">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 text-gray-700 border border-gray-300 rounded-md hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              className="px-4 py-2 bg-blue-500 text-white rounded-md hover:bg-blue-600"
            >
              Add Server
            </button>
          </div>
        </form>
        
        {/* Examples */}
        <div className="mt-6 pt-4 border-t border-gray-200">
          <h3 className="text-sm font-medium text-gray-700 mb-2">Examples:</h3>
          <div className="text-xs text-gray-600 space-y-2">
            <div>
              <strong>Filesystem:</strong> npx, args: "-y @modelcontextprotocol/server-filesystem /path"
            </div>
            <div>
              <strong>SQLite:</strong> uvx, args: "mcp-server-sqlite --db-path /path/to/db.sqlite"
            </div>
            <div>
              <strong>Git:</strong> npx, args: "-y @modelcontextprotocol/server-git /path/to/repo"
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default AddServerModal;
