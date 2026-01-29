/**
 * System command interface
 */
import React, { useState, useEffect } from 'react';
import wsService from '../services/websocket';

interface SystemCommandProps {
  onCommand: (command: string) => void;
}

interface CommandResponse {
  type: string;
  confirmation?: string;
  understood_intent?: string;
  task_id?: string;
  task_type?: string;
  message?: string;
  timestamp?: string;
}

const SystemCommand: React.FC<SystemCommandProps> = ({ onCommand }) => {
  const [command, setCommand] = useState('');
  const [history, setHistory] = useState<string[]>([]);
  const [responses, setResponses] = useState<CommandResponse[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    // Listen for system messages
    const handleSystemMessage = (message: any) => {
      if (message.type === 'command_processed') {
        setResponses(prev => [{
          type: 'processed',
          confirmation: message.data?.confirmation,
          understood_intent: message.data?.understood_intent,
          task_id: message.data?.task_id,
          task_type: message.data?.task_type,
          timestamp: message.timestamp
        }, ...prev].slice(0, 5));
        setIsProcessing(false);
      } else if (message.type === 'camera_started') {
        setResponses(prev => [{
          type: 'info',
          message: `📹 ${message.data?.message}`,
          timestamp: message.timestamp
        }, ...prev].slice(0, 5));
      } else if (message.type === 'camera_error') {
        setResponses(prev => [{
          type: 'error',
          message: `❌ ${message.data?.message}`,
          timestamp: message.timestamp
        }, ...prev].slice(0, 5));
        setIsProcessing(false);
      } else if (message.type === 'task_started') {
        setResponses(prev => [{
          type: 'started',
          message: message.data?.message,
          task_type: message.data?.task_type,
          timestamp: message.timestamp
        }, ...prev].slice(0, 5));
      } else if (message.type === 'task_alert') {
        setResponses(prev => [{
          type: 'alert',
          message: message.data?.alert_message,
          task_type: message.data?.task_type,
          timestamp: message.timestamp
        }, ...prev].slice(0, 5));
      } else if (message.type === 'command_error') {
        setResponses(prev => [{
          type: 'error',
          message: message.data?.message,
          timestamp: message.timestamp
        }, ...prev].slice(0, 5));
        setIsProcessing(false);
      }
    };

    wsService.addHandler('/ws/system', handleSystemMessage);

    return () => {
      wsService.removeHandler('/ws/system', handleSystemMessage);
    };
  }, []);


  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();

    if (command.trim()) {
      setHistory([...history, command]);
      setIsProcessing(true);
      onCommand(command);
      setCommand('');
    }
  };

  const quickCommands = [
    { label: '👀 Watch for people', command: 'Watch for any people entering the scene' },
    { label: '🚗 Detect vehicles', command: 'Alert me if you see any vehicles' },
    { label: '⚠️ Monitor suspicious activity', command: 'Monitor for suspicious activity' }
  ];

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="text-lg font-semibold">🤖 AI Command Center</h2>
        <p className="text-xs text-gray-400 mt-1">Ask me to monitor, detect, or analyze anything</p>
      </div>
      <div className="card-body">
        <form onSubmit={handleSubmit} className="mb-3">
          <div className="flex gap-2">
            <input
              type="text"
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              placeholder="e.g., Watch for people entering..."
              disabled={isProcessing}
              className="flex-1 px-3 py-2 bg-dark-900 border border-dark-700 rounded-md text-gray-100 placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-primary-600 focus:border-transparent disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={isProcessing}
              className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-md transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isProcessing ? '⏳' : 'Send'}
            </button>
          </div>
        </form>

        <div className="flex gap-2 flex-wrap mb-3">
          {quickCommands.map((cmd) => (
            <button
              key={cmd.command}
              onClick={() => {
                setIsProcessing(true);
                setHistory([...history, cmd.command]);
                onCommand(cmd.command);
              }}
              disabled={isProcessing}
              className="px-3 py-1 text-xs bg-dark-700 hover:bg-dark-600 text-gray-300 rounded transition-colors disabled:opacity-50"
            >
              {cmd.label}
            </button>
          ))}
        </div>

        {/* AI Responses */}
        {responses.length > 0 && (
          <div className="mt-4 pt-4 border-t border-dark-700">
            <h3 className="text-xs font-semibold text-gray-400 mb-2">AI Responses</h3>
            <div className="space-y-2 max-h-48 overflow-y-auto">
              {responses.map((response, index) => (
                <div
                  key={index}
                  className={`p-2 rounded text-xs ${
                    response.type === 'error'
                      ? 'bg-red-900/20 border border-red-800/30'
                      : response.type === 'alert'
                      ? 'bg-yellow-900/20 border border-yellow-800/30'
                      : response.type === 'info'
                      ? 'bg-blue-900/20 border border-blue-800/30'
                      : 'bg-primary-900/20 border border-primary-800/30'
                  }`}
                >
                  {response.confirmation && (
                    <div className="text-gray-200 mb-1">
                      ✓ {response.confirmation}
                    </div>
                  )}
                  {response.understood_intent && (
                    <div className="text-gray-400 text-xs italic">
                      Understanding: {response.understood_intent}
                    </div>
                  )}
                  {response.message && (
                    <div className="text-gray-300">
                      {response.message}
                    </div>
                  )}
                  {response.task_type && (
                    <div className="text-gray-500 text-xs mt-1">
                      Task: {response.task_type.replace('_', ' ')}
                    </div>
                  )}
                </div>
              ))}
            </div>
          </div>
        )}

        {history.length > 0 && (
          <div className="mt-4 pt-4 border-t border-dark-700">
            <h3 className="text-xs font-semibold text-gray-400 mb-2">Command History</h3>
            <div className="space-y-1 max-h-32 overflow-y-auto">
              {history.slice(-5).reverse().map((cmd, index) => (
                <div key={index} className="text-xs text-gray-500 font-mono">
                  {'>'} {cmd}
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SystemCommand;
