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

const quickCommands = [
  { label: 'Watch for people', command: 'Watch for any people entering the scene' },
  { label: 'Detect vehicles', command: 'Alert me if you see any vehicles' },
  { label: 'Monitor activity', command: 'Monitor for suspicious activity' },
];

const SystemCommand: React.FC<SystemCommandProps> = ({ onCommand }) => {
  const [command, setCommand] = useState('');
  const [history, setHistory] = useState<string[]>([]);
  const [responses, setResponses] = useState<CommandResponse[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    const handleSystemMessage = (message: any) => {
      if (message.type === 'command_processed') {
        setResponses((prev) => [{
          type: 'processed',
          confirmation: message.data?.confirmation,
          understood_intent: message.data?.understood_intent,
          task_id: message.data?.task_id,
          task_type: message.data?.task_type,
          timestamp: message.timestamp,
        }, ...prev].slice(0, 5));
        setIsProcessing(false);
      } else if (message.type === 'camera_started') {
        setResponses((prev) => [{ type: 'info', message: message.data?.message, timestamp: message.timestamp }, ...prev].slice(0, 5));
      } else if (message.type === 'camera_error') {
        setResponses((prev) => [{ type: 'error', message: message.data?.message, timestamp: message.timestamp }, ...prev].slice(0, 5));
        setIsProcessing(false);
      } else if (message.type === 'task_started') {
        setResponses((prev) => [{ type: 'started', message: message.data?.message, task_type: message.data?.task_type, timestamp: message.timestamp }, ...prev].slice(0, 5));
      } else if (message.type === 'task_alert') {
        setResponses((prev) => [{ type: 'alert', message: message.data?.alert_message, task_type: message.data?.task_type, timestamp: message.timestamp }, ...prev].slice(0, 5));
      } else if (message.type === 'command_error') {
        setResponses((prev) => [{ type: 'error', message: message.data?.message, timestamp: message.timestamp }, ...prev].slice(0, 5));
        setIsProcessing(false);
      }
    };

    wsService.addHandler('/ws/system', handleSystemMessage);
    return () => wsService.removeHandler('/ws/system', handleSystemMessage);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!command.trim()) return;
    setHistory((h) => [...h, command]);
    setIsProcessing(true);
    onCommand(command);
    setCommand('');
  };

  const responseStyle = (type: string) => {
    if (type === 'error') return 'bg-red-50 border-red-200 text-red-700';
    if (type === 'alert') return 'bg-orange-50 border-orange-200 text-orange-700';
    if (type === 'info') return 'bg-blue-50 border-blue-200 text-blue-700';
    return 'bg-gray-50 border-gray-200 text-gray-700';
  };

  return (
    <div className="card">
      <div className="card-header">
        <h2 className="text-base font-semibold text-gray-900">AI Command</h2>
        <p className="text-xs text-gray-400 mt-0.5">Give the AI instructions for what to monitor</p>
      </div>
      <div className="card-body space-y-3">
        <form onSubmit={handleSubmit}>
          <div className="flex gap-2">
            <input
              type="text"
              value={command}
              onChange={(e) => setCommand(e.target.value)}
              placeholder="e.g. Watch for people entering the room..."
              disabled={isProcessing}
              className="input flex-1"
            />
            <button
              type="submit"
              disabled={isProcessing || !command.trim()}
              className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isProcessing ? (
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                </svg>
              ) : 'Send'}
            </button>
          </div>
        </form>

        <div className="flex gap-2 flex-wrap">
          {quickCommands.map((cmd) => (
            <button
              key={cmd.command}
              onClick={() => {
                setIsProcessing(true);
                setHistory((h) => [...h, cmd.command]);
                onCommand(cmd.command);
              }}
              disabled={isProcessing}
              className="text-xs px-3 py-1.5 bg-gray-100 hover:bg-gray-200 text-gray-600 rounded-md transition-colors disabled:opacity-50"
            >
              {cmd.label}
            </button>
          ))}
        </div>

        {responses.length > 0 && (
          <div className="pt-3 border-t border-gray-100">
            <p className="text-xs font-medium text-gray-500 mb-2">Responses</p>
            <div className="space-y-2 max-h-40 overflow-y-auto">
              {responses.map((resp, i) => (
                <div key={i} className={`text-xs p-2 rounded-md border ${responseStyle(resp.type)}`}>
                  {resp.confirmation && <p className="font-medium mb-0.5">{resp.confirmation}</p>}
                  {resp.understood_intent && <p className="opacity-75 italic">Intent: {resp.understood_intent}</p>}
                  {resp.message && <p>{resp.message}</p>}
                  {resp.task_type && <p className="opacity-60 mt-0.5">Task: {resp.task_type.replace('_', ' ')}</p>}
                </div>
              ))}
            </div>
          </div>
        )}

        {history.length > 0 && (
          <div className="pt-3 border-t border-gray-100">
            <p className="text-xs font-medium text-gray-500 mb-2">Command history</p>
            <div className="space-y-1 max-h-24 overflow-y-auto">
              {history.slice(-5).reverse().map((cmd, i) => (
                <p key={i} className="text-xs text-gray-400 font-mono truncate">
                  &gt; {cmd}
                </p>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SystemCommand;
