// 对话消息
export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  timing?: Timing
  feedback?: 'positive' | 'negative' | null
}

// 引用来源
export interface Source {
  file: string
  section: string
  content_type: string
  chunk: string
  score: number
}

// 耗时统计
export interface Timing {
  retrieval_ms: number
  generation_ms: number
  total_ms: number
}

// Token用量
export interface Usage {
  prompt_tokens: number
  completion_tokens: number
  total_tokens: number
}

// 问答响应
export interface QueryResponse {
  request_id: string
  answer: string
  sources: Source[]
  usage: Usage
  timing: Timing
}

// WebSocket消息类型
export interface WSTokenMessage {
  type: 'token'
  content: string
}

export interface WSSourcesMessage {
  type: 'sources'
  sources: Source[]
}

export interface WSDoneMessage {
  type: 'done'
  usage: Usage
  timing: Timing
}

export interface WSErrorMessage {
  type: 'error'
  message: string
}

export type WSMessage = WSTokenMessage | WSSourcesMessage | WSDoneMessage | WSErrorMessage
