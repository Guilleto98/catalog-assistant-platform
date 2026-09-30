import { HttpClient, HttpParams } from '@angular/common/http';
import { inject, Injectable } from '@angular/core';
import { firstValueFrom } from 'rxjs';
import {
  Conversation,
  ConversationPage,
  MessagePage,
  SendRequest,
  SendResponse,
  SavedFilterList,
} from '../../../api/contracts';
import { API_BASE_URL } from '../../../core/api/config';
import { CHAT_PAGINATION } from '../../../core/constants/ui.constants';

@Injectable({ providedIn: 'root' })
export class ConversationsService {
  private readonly http = inject(HttpClient);
  private readonly base = inject(API_BASE_URL);
  listSavedFilters(): Promise<SavedFilterList> {
    return firstValueFrom(this.http.get<SavedFilterList>(`${this.base}/saved-filters`));
  }
  listConversations(
    page: number = CHAT_PAGINATION.FIRST_PAGE,
    pageSize = CHAT_PAGINATION.CONVERSATIONS_PER_PAGE,
  ): Promise<ConversationPage> {
    return firstValueFrom(
      this.http.get<ConversationPage>(`${this.base}/conversations`, {
        params: new HttpParams().set('page', page).set('pageSize', pageSize),
      }),
    );
  }
  createConversation(): Promise<Conversation> {
    return firstValueFrom(this.http.post<Conversation>(`${this.base}/conversations`, {}));
  }
  getConversation(id: string): Promise<Conversation> {
    return firstValueFrom(
      this.http.get<Conversation>(`${this.base}/conversations/${encodeURIComponent(id)}`),
    );
  }
  getMessages(
    id: string,
    page: number = CHAT_PAGINATION.FIRST_PAGE,
    pageSize = CHAT_PAGINATION.MESSAGES_PER_PAGE,
  ): Promise<MessagePage> {
    return firstValueFrom(
      this.http.get<MessagePage>(`${this.base}/conversations/${encodeURIComponent(id)}/messages`, {
        params: new HttpParams().set('page', page).set('pageSize', pageSize),
      }),
    );
  }
  sendMessage(id: string, request: SendRequest): Promise<SendResponse> {
    return firstValueFrom(
      this.http.post<SendResponse>(
        `${this.base}/conversations/${encodeURIComponent(id)}/messages`,
        request,
      ),
    );
  }
  archiveConversation(id: string): Promise<Conversation> {
    return firstValueFrom(
      this.http.post<Conversation>(
        `${this.base}/conversations/${encodeURIComponent(id)}/archive`,
        {},
      ),
    );
  }
}
