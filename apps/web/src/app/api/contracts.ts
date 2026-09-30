import type { components } from './generated/application-api';

type Schemas = components['schemas'];
export type CurrentUser = Schemas['CurrentUserDto'];
export type Conversation = Schemas['ConversationSummaryDto'];
export type Message = Schemas['MessageDto'];
export type SendRequest = Schemas['SendMessageRequest'];
export type SendResponse = Schemas['SendMessageResponse'];
export type ConversationPage = Schemas['PageDto_ConversationSummaryDto_'];
export type MessagePage = Schemas['PageDto_MessageDto_'];
export type UiEvent = Message['uiEvents'][number];
export type Payload<K extends UiEvent['type']> = Extract<UiEvent, { type: K }>['payload'];
export type SavedFilter = Schemas['SavedFilterView'];
export type SavedFilterList = Schemas['SavedFilterListPayload'];
