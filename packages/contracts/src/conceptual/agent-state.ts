export type FilterOperator =
  | 'eq'
  | 'neq'
  | 'in'
  | 'contains'
  | 'gte'
  | 'lte'
  | 'between'
  | 'is_null';

export interface SearchFilter {
  field: string;
  operator: FilterOperator;
  value?: unknown;
}

export interface SearchSort {
  field: string;
  direction: 'asc' | 'desc';
}

export interface CurrentSearch {
  filters: SearchFilter[];
  sort: SearchSort[];
  page: number;
  pageSize: number;
}

export interface AgentRequestContext {
  userId: string;
  conversationId: string;
}

export interface RecentEntity {
  type: 'ARTICLE' | 'SAVED_FILTER' | 'TECHNICAL_SHEET';
  id: string;
  label?: string;
}

export interface AgentState {
  conversationId: string;
  currentSearch: CurrentSearch | null;
  lastSearch: {
    articleCodes: string[];
    page: number;
    totalItems: number;
  } | null;
  selectedArticleCodes: string[];
  lastArticleCode: string | null;
  lastComparison: { codes: string[] } | null;
  lastSimilarity: {
    referenceCode?: string;
    features?: Record<string, unknown>;
    required?: Record<string, unknown>;
    eligibleCodes: string[];
    ineligibleCodes: string[];
  } | null;
  lastTechnicalSheet: {
    technicalSheetId: string;
    articleCode?: string;
  } | null;
  lastSavedFilter: { id: string; name: string } | null;
  recentEntities: RecentEntity[];
}

export const createEmptyAgentState = (conversationId: string): AgentState => ({
  conversationId,
  currentSearch: null,
  lastSearch: null,
  selectedArticleCodes: [],
  lastArticleCode: null,
  lastComparison: null,
  lastSimilarity: null,
  lastTechnicalSheet: null,
  lastSavedFilter: null,
  recentEntities: [],
});
