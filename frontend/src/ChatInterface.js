import React, { useState, useCallback } from 'react';
import axios from 'axios';
import { MessageCircle, Send, User, Bot, Settings } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import ModelSelector from './ModelSelector';

const API_BASE = 'http://localhost:8000';

const ChatInterface = React.memo(({ connectedServers, messages, setMessages, selectedModel, setSelectedModel }) => {
  const [inputMessage, setInputMessage] = useState('');
  const [isTyping, setIsTyping] = useState(false);

  const sendMessage = useCallback(async () => {
    if (!inputMessage.trim()) return;

    const newMessage = { role: 'user', content: inputMessage };
    setMessages(prev => [...prev, newMessage]);
    const messageToSend = inputMessage; // Capture the message before clearing
    setInputMessage('');
    setIsTyping(true);

    try {
      const response = await axios.post(`${API_BASE}/api/chat`, {
        message: messageToSend,
        history: messages,
        model: selectedModel || undefined
      });

      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: response.data.response 
      }]);
    } catch (error) {
      console.error('Failed to send message:', error);
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Sorry, I encountered an error processing your message. Make sure the backend server is running.' 
      }]);
    } finally {
      setIsTyping(false);
    }
  }, [inputMessage, messages, selectedModel, setMessages]);

  const handleKeyPress = useCallback((e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }, [sendMessage]);

  const handleInputChange = useCallback((e) => {
    setInputMessage(e.target.value);
  }, []);

  return (
    <div className="bg-white rounded-lg shadow-md h-[600px] flex flex-col">
      {/* Chat Header */}
      <div className="p-4 border-b border-gray-200 bg-gray-50 rounded-t-lg">
        <div className="flex items-center justify-between mb-2">
          <h2 className="text-xl font-semibold flex items-center">
            <MessageCircle className="w-5 h-5 mr-2 text-blue-600" />
            Chat with MCP Tools
          </h2>
          <Settings className="w-5 h-5 text-gray-400" />
        </div>
        
        <div className="flex items-center justify-between">
          <p className="text-sm text-gray-600">
            Connected servers: {connectedServers.length} | Available tools: {connectedServers.reduce((sum, s) => sum + (s.tools_count || 0), 0)}
          </p>
          
          <div className="flex items-center space-x-3">
            <span className="text-sm font-medium text-gray-700">Model:</span>
            <ModelSelector
              selectedModel={selectedModel}
              onModelChange={setSelectedModel}
              className="min-w-[200px]"
            />
          </div>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 ? (
          <div className="text-center text-gray-500 mt-8">
            <Bot className="w-16 h-16 mx-auto mb-4 text-gray-300" />
            <h3 className="text-lg font-semibold mb-2">Welcome to Universal MCP Host!</h3>
            <p className="mb-4">I can help you interact with your connected MCP servers.</p>
            <div className="text-sm text-left max-w-md mx-auto space-y-2 bg-gray-50 p-4 rounded-lg">
              <p className="font-medium">Try asking me to:</p>
              <ul className="list-disc list-inside space-y-1">
                <li>List files in a directory</li>
                <li>Read file contents</li>
                <li>Query databases</li>
                <li>Use any connected MCP server capabilities</li>
              </ul>
            </div>
          </div>
        ) : (
          messages.map((message, index) => (
            <div key={index} className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}>
              <div className={`max-w-[70%] rounded-lg p-4 ${
                message.role === 'user' 
                  ? 'bg-blue-500 text-white' 
                  : 'bg-gray-100 text-gray-800 border border-gray-200'
              }`}>
                <div className="flex items-start space-x-3">
                  {message.role === 'assistant' && <Bot className="w-5 h-5 mt-0.5 flex-shrink-0 text-gray-600" />}
                  {message.role === 'user' && <User className="w-5 h-5 mt-0.5 flex-shrink-0 text-white" />}
                  <div className="flex-1">
                    {message.role === 'assistant' ? (
                      <ReactMarkdown 
                        remarkPlugins={[remarkGfm]}
                        className="prose prose-sm max-w-none prose-pre:bg-gray-800 prose-pre:text-gray-100 prose-pre:overflow-x-auto prose-pre:whitespace-pre-wrap prose-code:bg-gray-100 prose-code:text-gray-800 prose-code:px-1 prose-code:py-0.5 prose-code:rounded prose-code:break-all"
                        components={{
                          code({node, inline, className, children, ...props}) {
                            return (
                              <code
                                className={`${className} ${inline ? 'break-all' : 'block overflow-x-auto whitespace-pre-wrap'}`}
                                {...props}
                              >
                                {children}
                              </code>
                            );
                          },
                          pre({children, ...props}) {
                            return (
                              <pre
                                className="overflow-x-auto whitespace-pre-wrap break-words max-w-full"
                                {...props}
                              >
                                {children}
                              </pre>
                            );
                          }
                        }}
                      >
                        {message.content}
                      </ReactMarkdown>
                    ) : (
                      <p className="whitespace-pre-wrap leading-relaxed break-words">{message.content}</p>
                    )}
                  </div>
                </div>
              </div>
            </div>
          ))
        )}
        
        {isTyping && (
          <div className="flex justify-start">
            <div className="bg-gray-100 text-gray-800 rounded-lg p-4 max-w-[70%] border border-gray-200">
              <div className="flex items-center space-x-3">
                <Bot className="w-5 h-5 text-gray-600" />
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.1s'}}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></div>
                </div>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Input Area */}
      <div className="p-4 border-t border-gray-200 bg-gray-50 rounded-b-lg">
        <div className="flex space-x-3">
          <input
            type="text"
            value={inputMessage}
            onChange={handleInputChange}
            onKeyPress={handleKeyPress}
            placeholder="Ask me to use MCP tools..."
            className="flex-1 px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
            disabled={isTyping}
            autoComplete="off"
          />
          <button
            onClick={sendMessage}
            disabled={!inputMessage.trim() || isTyping}
            className="px-6 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center"
          >
            <Send className="w-4 h-4" />
          </button>
        </div>
        {connectedServers.length === 0 && (
          <p className="text-xs text-amber-600 mt-2">⚠️ Connect to MCP servers first to enable tool capabilities</p>
        )}
      </div>
    </div>
  );
});

ChatInterface.displayName = 'ChatInterface';

export default ChatInterface;