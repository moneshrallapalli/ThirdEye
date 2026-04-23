import React, { useEffect, useRef, useState } from 'react';
import { useSurveillance } from '../contexts/SurveillanceContext';
import { formatDistanceToNow } from 'date-fns';
import wsService from '../services/websocket';
import { searchApi, SceneSearchResult, SceneSearchMatch } from '../services/api';
import { utcToDate } from '../utils/time';

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
  if (type === 'info') return 'bg-stone-50 border-stone-200 text-stone-700';
  return 'bg-stone-50 border-stone-200 text-stone-700';
};

const significanceBadgeClass = (score: number) => {
  if (score >= 80) return 'text-red-600 bg-red-50 border-red-200';
  if (score >= 50) return 'text-orange-600 bg-orange-50 border-orange-200';
  return 'text-stone-700 bg-stone-50 border-stone-200';
};

const similarityLabel = (score: number | null) => {
  if (score === null) return null;
  if (score >= 0.8) return { text: `${Math.round(score * 100)}% match`, cls: 'text-green-700 bg-green-50 border-green-200' };
  if (score >= 0.5) return { text: `${Math.round(score * 100)}% match`, cls: 'text-yellow-700 bg-yellow-50 border-yellow-200' };
  return { text: `${Math.round(score * 100)}% match`, cls: 'text-stone-500 bg-stone-50 border-stone-200' };
};

const IntelligencePage: React.FC = () => {
  const { narrations, handleSystemCommand } = useSurveillance();
  const scrollRef = useRef<HTMLDivElement>(null);
  const [activeTab, setActiveTab] = useState<'live' | 'search'>('live');

  // Live tab state
  const [command, setCommand] = useState('');
  const [history, setHistory] = useState<string[]>([]);
  const [responses, setResponses] = useState<CommandResponse[]>([]);
  const [isProcessing, setIsProcessing] = useState(false);

  // Search tab state
  const [searchQuery, setSearchQuery] = useState('');
  const [searchStart, setSearchStart] = useState('');
  const [searchEnd, setSearchEnd] = useState('');
  const [isSearching, setIsSearching] = useState(false);
  const [searchResult, setSearchResult] = useState<SceneSearchResult | null>(null);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [expandedMatch, setExpandedMatch] = useState<number | null>(null);

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

  const runSearch = async () => {
    if (!searchQuery.trim()) return;
    setIsSearching(true);
    setSearchError(null);
    setSearchResult(null);
    try {
      const result = await searchApi.scenes(
        searchQuery.trim(),
        searchStart || undefined,
        searchEnd || undefined,
      );
      setSearchResult(result);
    } catch (err: any) {
      setSearchError(err?.response?.data?.detail || err?.message || 'Search failed');
    } finally {
      setIsSearching(false);
    }
  };

  return (
    <div className="p-6 space-y-5 h-full flex flex-col">
      {/* Header + tabs */}
      <div className="flex items-end justify-between flex-shrink-0">
        <div>
          <h1 className="font-display text-xl font-semibold text-stone-900">Intelligence</h1>
          <p className="text-sm text-stone-500 mt-0.5">Scene analysis and AI command center</p>
        </div>
        <div className="flex gap-1 bg-stone-100 p-1 rounded-lg">
          <button
            onClick={() => setActiveTab('live')}
            className={`px-4 py-1.5 text-xs font-medium rounded-md transition-colors ${activeTab === 'live' ? 'bg-white text-stone-900 shadow-sm' : 'text-stone-500 hover:text-stone-700'}`}
          >
            Live
          </button>
          <button
            onClick={() => setActiveTab('search')}
            className={`px-4 py-1.5 text-xs font-medium rounded-md transition-colors ${activeTab === 'search' ? 'bg-white text-stone-900 shadow-sm' : 'text-stone-500 hover:text-stone-700'}`}
          >
            Scene Search
          </button>
        </div>
      </div>

      {/* Live tab */}
      {activeTab === 'live' && (
        <div className="grid grid-cols-5 gap-6 flex-1 min-h-0">
          {/* Scene narration */}
          <div className="col-span-3 bg-white border border-stone-200 rounded-lg flex flex-col overflow-hidden">
            <div className="px-5 py-4 border-b border-stone-100 flex items-center justify-between flex-shrink-0">
              <h2 className="text-sm font-semibold text-stone-900">Scene Analysis</h2>
              <span className="text-xs text-stone-400">{narrations.length} events</span>
            </div>
            <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-2">
              {narrations.length === 0 ? (
                <div className="h-full flex items-center justify-center">
                  <div className="text-center">
                    <svg className="w-8 h-8 mx-auto text-stone-300 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
                    </svg>
                    <p className="text-sm text-stone-400">Waiting for scene analysis...</p>
                    <p className="text-xs text-stone-300 mt-1">Start a camera to see live analysis</p>
                  </div>
                </div>
              ) : (
                narrations.map((entry) => (
                  <div key={entry.id} className="flex gap-3 p-3 bg-stone-50 rounded-lg border border-stone-100">
                    <div className="w-0.5 bg-stone-300 rounded-full flex-shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-1 flex-wrap">
                        <span className="text-xs font-medium text-stone-700">Camera {entry.cameraId}</span>
                        <span className="text-xs text-stone-400">
                          {formatDistanceToNow(utcToDate(entry.timestamp), { addSuffix: true })}
                        </span>
                        <span className={`badge border ${significanceBadgeClass(entry.significance)}`}>
                          {entry.significance}%
                        </span>
                      </div>
                      <p className="text-sm text-stone-700">{entry.description}</p>
                      {entry.detections > 0 && (
                        <p className="text-xs text-stone-400 mt-1">
                          {entry.detections} object{entry.detections !== 1 ? 's' : ''} detected
                        </p>
                      )}
                      {entry.context && (
                        <details className="mt-1 text-xs">
                          <summary className="cursor-pointer text-stone-700 hover:text-stone-900 font-medium">
                            View context
                          </summary>
                          <p className="mt-1 text-stone-500 pl-2 border-l border-stone-200">{entry.context}</p>
                        </details>
                      )}
                    </div>
                  </div>
                ))
              )}
            </div>
          </div>

          {/* AI Command */}
          <div className="col-span-2 bg-white border border-stone-200 rounded-lg flex flex-col overflow-hidden">
            <div className="px-5 py-4 border-b border-stone-100 flex-shrink-0">
              <h2 className="text-sm font-semibold text-stone-900">AI Command</h2>
              <p className="text-xs text-stone-400 mt-0.5">Direct the AI to monitor specific things</p>
            </div>
            <div className="flex-1 p-4 space-y-4 overflow-y-auto">
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

              <div>
                <p className="text-xs font-medium text-stone-500 mb-2">Quick commands</p>
                <div className="space-y-1.5">
                  {quickCommands.map((cmd) => (
                    <button
                      key={cmd.command}
                      onClick={() => submit(cmd.command)}
                      disabled={isProcessing}
                      className="w-full text-left text-xs px-3 py-2 bg-stone-50 hover:bg-stone-100 text-stone-700 rounded-md border border-stone-200 transition-colors disabled:opacity-50"
                    >
                      {cmd.label}
                    </button>
                  ))}
                </div>
              </div>

              {responses.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-stone-500 mb-2">Responses</p>
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

              {history.length > 0 && (
                <div>
                  <p className="text-xs font-medium text-stone-500 mb-2">History</p>
                  <div className="space-y-1">
                    {history.slice(-5).reverse().map((cmd, i) => (
                      <p key={i} className="text-xs text-stone-400 font-mono truncate">&gt; {cmd}</p>
                    ))}
                  </div>
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Scene Search tab */}
      {activeTab === 'search' && (
        <div className="flex-1 min-h-0 flex flex-col gap-4">
          {/* Search form */}
          <div className="bg-white border border-stone-200 rounded-lg p-5 flex-shrink-0">
            <h2 className="text-sm font-semibold text-stone-900 mb-3">Search past footage across all cameras</h2>
            <div className="flex gap-3 items-end flex-wrap">
              <div className="flex-1 min-w-48">
                <label className="block text-xs font-medium text-stone-500 mb-1">Describe the scene</label>
                <input
                  type="text"
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && runSearch()}
                  placeholder='e.g. "person in red jacket near the door"'
                  className="input w-full text-sm"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-stone-500 mb-1">From</label>
                <input
                  type="datetime-local"
                  value={searchStart}
                  onChange={(e) => setSearchStart(e.target.value)}
                  className="input text-xs"
                />
              </div>
              <div>
                <label className="block text-xs font-medium text-stone-500 mb-1">To</label>
                <input
                  type="datetime-local"
                  value={searchEnd}
                  onChange={(e) => setSearchEnd(e.target.value)}
                  className="input text-xs"
                />
              </div>
              <button
                onClick={runSearch}
                disabled={isSearching || !searchQuery.trim()}
                className="btn-primary disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
              >
                {isSearching ? (
                  <>
                    <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z" />
                    </svg>
                    Searching...
                  </>
                ) : 'Search'}
              </button>
            </div>
            <p className="text-xs text-stone-400 mt-2">
              Uses semantic search (ChromaDB) + text search across all cameras. Defaults to the last 7 days.
            </p>
          </div>

          {/* Error */}
          {searchError && (
            <div className="bg-red-50 border border-red-200 text-red-700 text-sm px-4 py-3 rounded-lg flex-shrink-0">
              {searchError}
            </div>
          )}

          {/* Results */}
          {searchResult && (
            <div className="flex-1 min-h-0 flex flex-col gap-4 overflow-y-auto">
              {/* Claude's answer */}
              <div className="bg-stone-50 border border-stone-200 rounded-lg p-4 flex-shrink-0">
                <div className="flex items-center justify-between mb-2">
                  <span className="text-xs font-semibold text-stone-700 uppercase tracking-wide">AI Answer</span>
                  <span className="text-xs text-stone-500">{searchResult.total_matches} event{searchResult.total_matches !== 1 ? 's' : ''} found</span>
                </div>
                <p className="text-sm text-stone-900 leading-relaxed whitespace-pre-line">{searchResult.answer}</p>
                <p className="text-xs text-stone-400 mt-2">
                  Searched {utcToDate(searchResult.time_range.start).toLocaleDateString()} → {utcToDate(searchResult.time_range.end).toLocaleDateString()}
                </p>
              </div>

              {/* Match list */}
              {searchResult.matches.length > 0 && (
                <div className="bg-white border border-stone-200 rounded-lg overflow-hidden flex-shrink-0">
                  <div className="px-5 py-3 border-b border-stone-100">
                    <h3 className="text-xs font-semibold text-stone-700">Matching events</h3>
                  </div>
                  <div className="divide-y divide-stone-100">
                    {searchResult.matches.map((match: SceneSearchMatch) => {
                      const sim = similarityLabel(match.semantic_similarity);
                      const isExpanded = expandedMatch === match.event_id;
                      return (
                        <div key={match.event_id} className="px-5 py-3">
                          <div
                            className="flex items-start gap-3 cursor-pointer"
                            onClick={() => setExpandedMatch(isExpanded ? null : match.event_id)}
                          >
                            {/* Camera + time */}
                            <div className="flex-1 min-w-0">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="text-xs font-semibold text-stone-800">{match.camera_name}</span>
                                {match.camera_location && (
                                  <span className="text-xs text-stone-400">{match.camera_location}</span>
                                )}
                                <span className="text-xs text-stone-500 font-mono">
                                  {utcToDate(match.timestamp).toLocaleString()}
                                </span>
                                {sim && (
                                  <span className={`text-xs px-1.5 py-0.5 rounded border font-medium ${sim.cls}`}>
                                    {sim.text}
                                  </span>
                                )}
                                {match.source === 'semantic' && !sim && (
                                  <span className="text-xs text-stone-400 italic">semantic</span>
                                )}
                                {match.significance >= 50 && (
                                  <span className={`badge border ${significanceBadgeClass(match.significance)}`}>
                                    {match.significance}
                                  </span>
                                )}
                                {match.is_anomaly && (
                                  <span className="text-xs px-1.5 py-0.5 rounded border bg-red-50 border-red-200 text-red-600 font-medium">
                                    anomaly
                                  </span>
                                )}
                              </div>
                              <p className="text-xs text-stone-600 mt-1 line-clamp-2">{match.scene_description}</p>
                            </div>
                            {/* Expand chevron */}
                            <svg
                              className={`w-4 h-4 text-stone-400 flex-shrink-0 mt-0.5 transition-transform ${isExpanded ? 'rotate-180' : ''}`}
                              fill="none" stroke="currentColor" viewBox="0 0 24 24"
                            >
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                            </svg>
                          </div>

                          {/* Expanded frame */}
                          {isExpanded && match.frame_url && (
                            <div className="mt-3 pl-0">
                              <img
                                src={`http://localhost:8000${match.frame_url}`}
                                alt={`Frame from ${match.camera_name}`}
                                className="rounded-md border border-stone-200 max-h-48 object-cover"
                                onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }}
                              />
                            </div>
                          )}
                          {isExpanded && !match.frame_url && (
                            <p className="text-xs text-stone-400 mt-2 pl-0 italic">No saved frame for this event.</p>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Empty state */}
          {!searchResult && !isSearching && !searchError && (
            <div className="flex-1 flex items-center justify-center">
              <div className="text-center">
                <svg className="w-10 h-10 mx-auto text-stone-200 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
                </svg>
                <p className="text-sm text-stone-400">Describe a scene to find when it happened</p>
                <p className="text-xs text-stone-300 mt-1">e.g. "someone left a bag unattended" or "vehicle parked at entrance"</p>
              </div>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default IntelligencePage;
