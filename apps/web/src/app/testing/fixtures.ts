import { Conversation, CurrentUser, Message, SendResponse } from '../api/contracts';
export const user: CurrentUser = {
  id: 'u1',
  email: 'test@example.test',
  role: 'CLIENT_USER',
  organization: { id: 'o1', name: 'Organización de prueba' },
};
export const conversation: Conversation = {
  id: 'c1',
  title: 'Nueva conversación',
  status: 'ACTIVE',
  preview: null,
  createdAt: '2026-09-30T12:00:00Z',
  updatedAt: '2026-09-30T12:00:00Z',
  lastMessageAt: null,
};
export const message: Message = {
  id: 'm1',
  conversationId: 'c1',
  role: 'USER',
  messageType: 'TEXT',
  text: 'China',
  attachments: [],
  uiEvents: [],
  createdAt: '2026-09-30T12:00:00Z',
};
export const sent: SendResponse = {
  userMessage: message,
  assistantMessage: { ...message, id: 'm2', role: 'ASSISTANT', text: 'Respuesta' },
  run: { id: 'r1', status: 'COMPLETED', error: null },
};
