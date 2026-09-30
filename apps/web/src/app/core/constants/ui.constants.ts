import type {
  Conversation,
  CurrentUser,
  Message,
  Payload,
  SendResponse,
  UiEvent,
} from '../../api/contracts';
import { HttpStatusCode } from '@angular/common/http';

export const HTTP_STATUS = {
  NETWORK_ERROR: 0,
  UNAUTHORIZED: HttpStatusCode.Unauthorized,
  FORBIDDEN: HttpStatusCode.Forbidden,
  NOT_FOUND: HttpStatusCode.NotFound,
  INTERNAL_SERVER_ERROR: HttpStatusCode.InternalServerError,
} as const;

export const CHAT_PAGINATION = {
  FIRST_PAGE: 1,
  INITIAL_PAGE_CURSOR: 0,
  PAGE_INDEX_ORIGIN: 1,
  CONVERSATIONS_PER_PAGE: 20,
  MESSAGES_PER_PAGE: 100,
} as const;

export const CHAT_INPUT_POLICY = {
  MAX_MESSAGE_LENGTH: 20_000,
  FILTER_COMMAND_PREFIX: '/',
} as const;

export const CHAT_SCROLL_POLICY = {
  BOTTOM_THRESHOLD_PX: 140,
  USER_INTENT_WINDOW_MS: 600,
} as const;

export const CHAT_MENU_POLICY = {
  OPEN_DELAY_MS: 0,
} as const;

export const LIST_PRESENTATION = {
  POSITION_ORIGIN: 1,
} as const;

export const STATE_POLICY = {
  REVISION_INCREMENT: 1,
} as const;

export const NAVIGATION_DELTA = {
  PREVIOUS: -1,
  NEXT: 1,
} as const;

export const KEYBOARD_KEY = {
  ARROW_DOWN: 'ArrowDown',
  ARROW_UP: 'ArrowUp',
  ENTER: 'Enter',
  ESCAPE: 'Escape',
} as const;

export const AUTH_STATUS = {
  LOADING: 'loading',
  READY: 'ready',
  UNAVAILABLE: 'unavailable',
} as const;
export type AuthStatus = (typeof AUTH_STATUS)[keyof typeof AUTH_STATUS];

export const SESSION_REASON = {
  EXPIRED: 'expired',
  LOGOUT: 'logout',
} as const;

export const ACCOUNT_ROLE = {
  CLIENT_USER: 'CLIENT_USER',
  INTERNAL_ADMIN: 'INTERNAL_ADMIN',
} as const satisfies Record<string, CurrentUser['role']>;

export const CONVERSATION_STATUS = {
  ACTIVE: 'ACTIVE',
  ARCHIVED: 'ARCHIVED',
} as const satisfies Record<string, Conversation['status']>;

export const MESSAGE_ROLE = {
  USER: 'USER',
  ASSISTANT: 'ASSISTANT',
  SYSTEM_EVENT: 'SYSTEM_EVENT',
} as const satisfies Record<string, Message['role']>;

export const AGENT_RUN_STATUS = {
  STARTED: 'STARTED',
  COMPLETED: 'COMPLETED',
  FAILED: 'FAILED',
} as const satisfies Record<string, SendResponse['run']['status']>;

export const COMPARISON_STATUS = {
  SAME: 'SAME',
  DIFFERENT: 'DIFFERENT',
} as const satisfies Record<string, Payload<'ARTICLE_COMPARISON'>['rows'][number]['status']>;

export const SIMILARITY_STATUS = {
  MATCH: 'MATCH',
  MISMATCH: 'MISMATCH',
  NOT_AVAILABLE: 'NOT_AVAILABLE',
} as const satisfies Record<
  string,
  Payload<'SIMILARITY_RESULTS'>['eligibleCandidates'][number]['criteria'][number]['status']
>;

export const DRAFT_STATUS = {
  DRAFT: 'DRAFT',
  NEEDS_REVIEW: 'NEEDS_REVIEW',
  READY: 'READY',
} as const satisfies Record<string, Payload<'REQUEST_DRAFT'>['status']>;

export const DRAFT_FIELD_STATUS = {
  PROPOSED: 'PROPOSED',
  CONFIRMED: 'CONFIRMED',
  CORRECTED: 'CORRECTED',
  REJECTED: 'REJECTED',
  NEEDS_CLARIFICATION: 'NEEDS_CLARIFICATION',
} as const satisfies Record<string, Payload<'REQUEST_DRAFT'>['fields'][number]['status']>;

export const DOCUMENT_SOURCE_TYPE = {
  PDF: 'PDF',
  SPREADSHEET: 'SPREADSHEET',
  USER: 'USER',
} as const satisfies Record<string, Payload<'REQUEST_DRAFT'>['fields'][number]['source']['type']>;

export const UI_EVENT_SCHEMA_VERSION: UiEvent['schemaVersion'] = 1;

export const UI_EVENT_TYPE = {
  ARTICLE_SEARCH_RESULTS: 'ARTICLE_SEARCH_RESULTS',
  ARTICLE_DETAIL: 'ARTICLE_DETAIL',
  ARTICLE_COMPARISON: 'ARTICLE_COMPARISON',
  SIMILARITY_RESULTS: 'SIMILARITY_RESULTS',
  TECHNICAL_SHEET: 'TECHNICAL_SHEET',
  REQUEST_DRAFT: 'REQUEST_DRAFT',
  SAVED_FILTER_LIST: 'SAVED_FILTER_LIST',
  SAVED_FILTER_CREATED: 'SAVED_FILTER_CREATED',
  SAVED_FILTER_DELETED: 'SAVED_FILTER_DELETED',
  ATTACHMENT_STATUS: 'ATTACHMENT_STATUS',
  ERROR: 'ERROR',
} as const satisfies Record<string, UiEvent['type']>;
