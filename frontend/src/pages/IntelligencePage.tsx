import React, { useEffect, useRef, useState } from 'react';
import { useSurveillance } from '../contexts/SurveillanceContext';
import { formatDistanceToNow } from 'date-fns';
import wsService from '../services/websocket';

interface CommandResponse {
  type: string;
  confirmation?: string;
  understood_intent?: string;
  task_type?: string;
  message?: string;
  timestamp?: string;
}

const quickCommands = [
  { label: 'Watch for people', command: 'Watch for any people entering the scene' },
  { label: 'Detect vehicles', command: 'Alert me if you see any vehicles' },
  { label: 'Monitor activity', command: 'Monitor for suspicious activity' },
];

const responseStyle = (type: string) => {
  if (type === 'error') return 'bg-red-50 border-red-200 text-red-700';
  if (type === 'alert') return 'bg-orange-50 border-orange-200 text-orange-700';
  if (type === 'info') return 'bg-blue-50 border-blue-200 text-blue-700';
  return 'bg-gray-50 border-gray-200 text-gray-700';
};

const significanceBadgeClass = (score: number) => {
  if (score >= 80) return 'text-red-600 bg-red-50 border-red-200';
  if (score >= 50) return 'text-orange-600 bg-orange-50 border-orange-200';
  return 'text-blue-600 bg-blue-50 border-blue-200';
};

const IntelligencePage: React.FC = () => {
  const { narrations, handleSystemCommand } = useSurveillance();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [command, setCommand] = useState('');
  const [history, setHistory] = useState<string[]>([]);
  const [responses, setResponses] = useState<CommandResponse[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [narrations]);

  useEffect(() => {
    const handler = (message: any) => {
      if (message.type === 'command_processed') {
        setResponses((p) => [{ type: 'processed', confirmation: message.data?.confirmation, understood_intent: message.data?.understood_intent, task_type: message.data?.task_type, timestamp: message.timestamp }, ...p].slice(0, 5));
        setIsProcessing(false);
      } else if (message.type === 'task_started' || message.type === 'camera_started') {
        setResponses((p) => [{ type: 'info', message: message.data?.message, timestamp: message.timestamp }, ...p].slice(0, 5));
      } else if (message.type === 'task_alert') {
        setResponses((p) => [{ type: 'alert', message: message.data?.alert_message, task_type: message.data?.task_type, timestamp: message.timestamp }, ...p].slice(0, 5));
      } else if (message.type === 'camera_error' || message.type === 'command_error') {
        setResponses((p) => [{ type: 'error', message: message.data?.message, timestamp: message.timestamp }, ...p].slice(0, 5));
        setIsProcessing(false);
      }
    };
    wsService.addHandler('/ws/system', handler);
    return () => wsService.removeHandler('/ws/system', handler);
  }, []);

  const submit = (cmd: string) => {
    if (!cmd.trim()) return;
    setHistory((h) => [...h, cmd]);
    setIsProcessing(true);
    handleSystemCommand(cmd);
    setCommand('');
  };

  return (
    <div className="p-6 space-y-5 h-full">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">Intelligence</h1>
        <p className="text-sm text-gray-500 mt-0.5">Scene analysis and AI command center</p>
      </div>

      <div className="grid grid-cols-5 gap-6" style={{ height: 'calc(100vh - 180px)' }}>
        {/* Scene narration — left 3/5 */}
        <div className="col-span-3 bg-white border border-gray-200 rounded-lg flex flex-col overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100 flex items-center justify-between flex-shrink-0">
            <h2 className="text-sm font-semibold text-gray-900">Scene Analysis</h2>
            <span className="text-xs text-gray-400">{narrations.length} events</span>
          </div>

          <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-2">
            {narrations.length === 0 ? (
              <div className="h-full flex items-center justify-center">
                <div className="text-center">
                  <svg className="w-8 h-8 mx-auto text-gray-300 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                  </svg>
                  <p className="text-sm text-gray-400">Waiting for scene analysis...</p>
                  <p className="text-xs text-gray-300 mt-1">Start a camera to see live analysis</p>
                </div>
              </div>
            ) : (
              narrations.map((entry) => (
                <div key={entry.id} className="flex gap-3 p-3 bg-gray-50 rounded-lg border border-gray-100">
                  <div className="w-0.5 bg-blue-200 rounded-full flex-shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1 flex-wrap">
                      <span className="text-xs font-medium text-gray-700">Camera {entry.cameraId}</span>
                      <span className="text-xs text-gray-400">
                        {formatDistanceToNow(new Date(entry.timestamp), { addSuffix: true })}
                      </span>
                      <span className={`badge border ${significanceBadgeClass(entry.significance)}`}>
                        {entry.significance}%
                      </span>
                    </div>
                    <p className="text-sm text-gray-700">{entry.description}</p>
                    {entry.detections > 0 && (
                      <p className="text-xs text-gray-400 mt-1">
                        {entry.detections} object{entry.detections !== 1 ? 's' : ''} detected
                      </p>
                    )}
                    {entry.context && (
                      <details className="mt-1 text-xs">
                        <summary className="cursor-pointer text-blue-600 hover:text-blue-700 font-medium">
                          View context
                        </summary>
                        <p className="mt-1 text-gray-500 pl-2 border-l border-gray-200">{entry.context}</p>
                      </details>
                    )}
                  </div>
                </div>
              ))
            )}
          </div>
        </div>

        {/* AI Command — right 2/5 */}
        <div className="col-span-2 bg-white border border-gray-200 rounded-lg flex flex-col overflow-hidden">
          <div className="px-5 py-4 border-b border-gray-100 flex-shrink-0">
            <h2 className="text-sm font-semibold text-gray-900">AI Command</h2>
            <p className="text-xs text-gray-400 mt-0.5">Direct the AI to monitor specific things</p>
          </div>

          <div className="flex-1 p-4 space-y-4 overflow-y-auto">
            {/* Input */}
            <form onSubmit={(e) => { e.preventDefault(); submit(command); }}>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={command}
                  onChange={(e) => setCommand(e.target.value)}
                  placeholder="e.g. Watch for people entering..."
                  disabled={isProcessing}
                  className="input flex-1 text-xs"
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

            {/* Quick commands */}
            <div>
              <p className="text-xs font-medium text-gray-500 mb-2">Quick commands</p>
              <div className="space-y-1.5">
                {quickCommands.map((cmd) => (
                  <button
                    key={cmd.command}
                    onClick={() => submit(cmd.command)}
                    disabled={isProcessing}
                    className="w-full text-left text-xs px-3 py-2 bg-gray-50 hover:bg-gray-100 text-gray-700 rounded-md border border-gray-200 transition-colors disabled:opacity-50"
                  >
                    {cmd.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Responses */}
            {responses.length > 0 && (
              <div>
                <p className="text-xs font-medium text-gray-500 mb-2">Responses</p>
                <div className="space-y-2">
                  {responses.map((resp, i) => (
                    <div key={i} className={`text-xs p-2.5 rounded-md border ${responseStyle(resp.type)}`}>
                      {resp.confirmation && <p className="font-medium mb-0.5">{resp.confirmation}</p>}
                      {resp.understood_intent && <p className="opacity-75 italic">Intent: {resp.understood_intent}</p>}
                      {resp.message && <p>{resp.message}</p>}
                      {resp.task_type && <p className="opacity-60 mt-0.5">Task: {resp.task_type.replace('_', ' ')}</p>}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* History */}
            {history.length > 0 && (
              <div>
                <p className="text-xs font-medium text-gray-500 mb-2">History</p>
                <div className="space-y-1">
                  {history.slice(-5).reverse().map((cmd, i) => (
                    <p key={i} className="text-xs text-gray-400 font-mono truncate">&gt; {cmd}</p>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default IntelligencePage;
