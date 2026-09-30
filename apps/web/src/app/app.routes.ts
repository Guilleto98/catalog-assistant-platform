import { Routes } from '@angular/router';
import { authGuard, guestGuard } from './core/auth/guards';

export const routes: Routes = [
  {
    path: 'login',
    canActivate: [guestGuard],
    loadComponent: () => import('./features/login/login.page').then((m) => m.LoginPage),
  },
  {
    path: 'chat',
    canActivate: [authGuard],
    loadComponent: () => import('./features/chat/pages/chat.page').then((m) => m.ChatPage),
  },
  {
    path: 'chat/:conversationId',
    canActivate: [authGuard],
    loadComponent: () => import('./features/chat/pages/chat.page').then((m) => m.ChatPage),
  },
  { path: '', pathMatch: 'full', redirectTo: 'chat' },
  { path: '**', redirectTo: 'chat' },
];
