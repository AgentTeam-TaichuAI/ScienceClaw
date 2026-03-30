import type { FileInfo } from '../api/file';

export type AgentSSEEvent = {
  event:
    | 'tool'
    | 'step'
    | 'message'
    | 'error'
    | 'done'
    | 'title'
    | 'wait'
    | 'plan'
    | 'attachments'
    | 'thinking'
    | 'message_chunk'
    | 'message_chunk_done'
    | 'skill_required'
    | 'skill_read'
    | 'skill_missing'
    | 'skill_save_prompt'
    | 'tool_save_prompt';
  data:
    | ToolEventData
    | StepEventData
    | MessageEventData
    | ErrorEventData
    | DoneEventData
    | TitleEventData
    | WaitEventData
    | PlanEventData
    | ThinkingEventData
    | MessageChunkEventData
    | SkillUsageEventData
    | SkillSavePromptEventData
    | ToolSavePromptEventData;
}

export interface BaseEventData {
  event_id: string;
  timestamp: number;
}

/** 工具元数据（图标、分类、描述） */
export interface ToolMetaData {
  icon: string;
  category: string;
  description: string;
  sandbox?: boolean;
}

export interface ToolEventData extends BaseEventData {
  tool_call_id: string;
  name: string;
  status: "calling" | "called";
  function: string;
  args: {[key: string]: any};
  content?: any;
  /** 工具调用耗时（毫秒），仅 status=called 时存在 */
  duration_ms?: number;
  /** 工具元数据（图标、分类、描述） */
  tool_meta?: ToolMetaData;
}

export interface StepEventData extends BaseEventData {
  status: "pending" | "running" | "in_progress" | "completed" | "failed"
  id: string
  description: string
  tools?: ToolEventData[]
}

export interface MessageEventData extends BaseEventData {
  content: string;
  role: "user" | "assistant";
  attachments: FileInfo[];
}

export interface ErrorEventData extends BaseEventData {
  error: string;
}

/** 统计信息 */
export interface StatisticsData {
  total_duration_ms?: number;
  tool_call_count?: number;
  input_tokens?: number;
  output_tokens?: number;
  token_count?: number;
}

/** 轮次文件信息（done 事件中携带） */
export interface RoundFileInfo {
  file_id: string;
  filename: string;
  relative_path: string;
  size: number;
  upload_date: string;
  file_url: string;
  category: 'output' | 'research_data';
}

export interface DoneEventData extends BaseEventData {
  /** 执行统计信息 */
  statistics?: StatisticsData;
  /** 本轮新增/修改的文件列表 */
  round_files?: RoundFileInfo[];
  status?: "completed" | "failed";
  error?: string | null;
}

export interface WaitEventData extends BaseEventData {
}

export interface TitleEventData extends BaseEventData {
  title: string;
}

export interface PlanEventData extends BaseEventData {
  steps: StepEventData[];
}

/** 思考过程事件 */
export interface ThinkingEventData extends BaseEventData {
  content: string;
}

export interface MessageChunkEventData extends BaseEventData {
  content: string;
}

export interface SkillUsageEventData extends BaseEventData {
  skill_name?: string;
  required_skills?: string[];
  read_skills?: string[];
  missing_required_skills?: string[];
}

export interface SkillSavePromptEventData extends BaseEventData {
  skill_name?: string;
}

export interface ToolSavePromptEventData extends BaseEventData {
  tool_name?: string;
  replaces?: string | null;
}
