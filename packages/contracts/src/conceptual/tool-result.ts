export type ToolErrorCategory =
  | 'VALIDATION'
  | 'NOT_FOUND'
  | 'UNAUTHORIZED'
  | 'FORBIDDEN'
  | 'UPSTREAM'
  | 'TIMEOUT'
  | 'UNKNOWN';

export interface ToolError {
  code: string;
  message: string;
  category: ToolErrorCategory;
  retryable: boolean;
  details?: Record<string, unknown>;
}

export type ToolResult<T> =
  | { ok: true; data: T }
  | { ok: false; error: ToolError };
