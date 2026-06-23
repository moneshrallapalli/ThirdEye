/**
 * Type definitions for ThirdEye Intelligent Monitoring System
 */

export enum AlertSeverity {
  CRITICAL = "CRITICAL",
  WARNING = "WARNING",
  INFO = "INFO",
  SYSTEM = "SYSTEM"
}

export interface Camera {
  id: number;
  name: string;
  location: string;
  stream_url?: string;
  is_active: boolean;
  fps: number;
  resolution_width: number;
  resolution_height: number;
  created_at: string;
  updated_at: string;
}

export interface Detection {
  id: number;
  object_type: string;
  object_label: string;
  confidence_score: number;
  bounding_box?: {
    x: number;
    y: number;
    width: number;
    height: number;
  };
  attributes?: string[];
  location?: string;
}

export interface Event {
  id: number;
  camera_id: number;
  timestamp: string;
  event_type: string;
  description: string;
  scene_description: string;
  significance_score: number;
  severity: AlertSeverity;
  context_summary?: string;
  is_anomaly: boolean;
  is_dismissed: boolean;
  detections?: Detection[];
}

export interface Alert {
  id: number | string;
  event_id?: number;
  severity: AlertSeverity;
  title: string;
  message: string;
  timestamp: string;
  is_read: boolean;
  is_dismissed?: boolean;
  acknowledged_at?: string;
  response_time_seconds?: number;
  camera_id?: number;
  // Image support fields
  significance?: number;
  frame_url?: string;
  frame_path?: string;
  frame_base64?: string;
  detections?: Detection[];
  detected_objects?: string[];
  // Reasoning / provenance so the UI can explain *why* the alert fired
  user_query?: string;
  query_confidence?: number;
  query_details?: string;
  claude_reasoning?: string;
  scene_description?: string;
  activity?: string;
  reasoning?: string;
  alert_type?: string;
}

export interface LiveFeedUpdate {
  type: "live_feed_update";
  camera_id: number;
  timestamp: string;
  frame: string; // Base64 encoded
  analysis: {
    scene_description: string;
    detections: Detection[];
    significance: number;
    activity?: string;
    changes?: string;
  };
}

export interface AnalysisUpdate {
  type: "analysis_update";
  timestamp: string;
  analysis: {
    camera_id: number;
    scene_description: string;
    significance: number;
    detections: number;
    context?: string;
  };
}

export interface SummaryStats {
  period_hours: number;
  total_events: number;
  critical_alerts: number;
  warning_alerts: number;
  info_alerts: number;
  avg_response_time_seconds: number;
  active_cameras: number;
  context_stats: {
    total_scenes: number;
    total_patterns: number;
  };
}

export interface CameraTask {
  id: number;
  camera_id: number;
  command: string;
  task_type: string;
  is_default: boolean;
  is_active: boolean;
  priority: number;
  source?: 'manual' | 'ai_command' | string;
  original_command?: string | null;
  created_at?: string;
}

export interface WebSocketMessage {
  type: string;
  timestamp: string;
  data?: any;
  alert?: Alert;
  analysis?: any;
}
