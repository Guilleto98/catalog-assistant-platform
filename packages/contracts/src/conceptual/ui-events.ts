import type { SearchFilter } from './agent-state';

export interface ArticleUiSummary {
  code: string;
  name: string;
  market?: string | null;
  temperature?: string | null;
}

export type AgentUiEvent =
  | {
      type: 'ARTICLE_SEARCH_RESULTS';
      data: { filters: SearchFilter[]; articles: ArticleUiSummary[]; totalItems: number };
    }
  | { type: 'ARTICLE_DETAIL'; data: { articleCode: string } }
  | { type: 'ARTICLE_COMPARISON'; data: { articleCodes: string[] } }
  | {
      type: 'SIMILARITY_RESULTS';
      data: { eligibleCodes: string[]; ineligibleCodes: string[] };
    }
  | {
      type: 'TECHNICAL_SHEET';
      data: { technicalSheetId: string; articleCode?: string };
    }
  | { type: 'SAVED_FILTER_CREATED'; data: { id: string; name: string } }
  | { type: 'SAVED_FILTER_LIST'; data: { filters: Array<{ id: string; name: string }> } }
  | { type: 'CLARIFICATION'; data: { question: string } }
  | { type: 'ERROR'; data: { code: string; retryable: boolean } };

export interface AgentResponse {
  message: string;
  ui?: AgentUiEvent;
}
