import React, { useState, useEffect } from 'react';
import { ChevronDown, Bot, Cpu, Cloud } from 'lucide-react';

const ModelSelector = ({ selectedModel, onModelChange, className = "" }) => {
  const [models, setModels] = useState([]); // Initialize as empty array
  const [isOpen, setIsOpen] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    const fetchModels = async () => {
      try {
        setIsLoading(true);
        setError(null);
        console.log('Fetching models from API...');
        
        const response = await fetch('http://localhost:8000/api/models');
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }
        
        const data = await response.json();
        console.log('Models API response:', data);
        
        // Ensure data is an array
        const modelArray = Array.isArray(data) ? data : [];
        setModels(modelArray);
        
        // If no model is selected, select the first one
        if (!selectedModel && modelArray.length > 0) {
          onModelChange(modelArray[0].id);
        }
      } catch (error) {
        console.error('Failed to fetch models:', error);
        setError(error.message);
        setModels([]); // Ensure it's always an array
      } finally {
        setIsLoading(false);
      }
    };

    fetchModels();
  }, [selectedModel, onModelChange]);

  const getProviderIcon = (provider) => {
    switch (provider.toLowerCase()) {
      case 'openai':
        return <Cloud className="w-4 h-4 text-green-600" />;
      case 'anthropic':
        return <Bot className="w-4 h-4 text-orange-600" />;
      case 'ollama':
        return <Cpu className="w-4 h-4 text-blue-600" />;
      default:
        return <Bot className="w-4 h-4 text-gray-600" />;
    }
  };

  // Ensure models is always an array before using .find()
  const selectedModelInfo = Array.isArray(models) ? models.find(m => m.id === selectedModel) : null;

  if (isLoading) {
    return (
      <div className={`flex items-center space-x-2 ${className}`}>
        <div className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"></div>
        <span className="text-sm text-gray-600">Loading models...</span>
      </div>
    );
  }

  if (error) {
    return (
      <div className={`flex items-center space-x-2 text-red-600 ${className}`}>
        <Bot className="w-4 h-4" />
        <span className="text-sm">Error loading models</span>
      </div>
    );
  }

  if (models.length === 0 && !isLoading) {
    return (
      <div className={`flex items-center space-x-2 text-amber-600 ${className}`}>
        <Bot className="w-4 h-4" />
        <span className="text-sm">No models available</span>
      </div>
    );
  }

  return (
    <div className={`relative ${className}`}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center justify-between w-full px-3 py-2 text-sm bg-white border border-gray-300 rounded-lg hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
      >
        <div className="flex items-center space-x-2">
          {selectedModelInfo && getProviderIcon(selectedModelInfo.provider)}
          <span className="font-medium">
            {selectedModelInfo ? selectedModelInfo.name : 'Select Model'}
          </span>
          {selectedModelInfo && (
            <span className="text-xs text-gray-500">
              ({selectedModelInfo.provider})
            </span>
          )}
        </div>
        <ChevronDown className={`w-4 h-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute z-50 w-full mt-1 bg-white border border-gray-300 rounded-lg shadow-lg max-h-60 overflow-y-auto">
          {models.map((model) => (
            <button
              key={model.id}
              onClick={() => {
                onModelChange(model.id);
                setIsOpen(false);
              }}
              className={`w-full px-3 py-2 text-left hover:bg-gray-50 flex items-center space-x-2 ${
                selectedModel === model.id ? 'bg-blue-50 text-blue-700' : 'text-gray-700'
              }`}
            >
              {getProviderIcon(model.provider)}
              <div className="flex-1">
                <div className="font-medium">{model.name}</div>
                <div className="text-xs text-gray-500">
                  {model.provider}
                  {model.description && ` • ${model.description}`}
                </div>
              </div>
              {selectedModel === model.id && (
                <div className="w-2 h-2 bg-blue-600 rounded-full"></div>
              )}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default ModelSelector;
