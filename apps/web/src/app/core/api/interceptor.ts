import { HttpContextToken, HttpErrorResponse, HttpInterceptorFn } from '@angular/common/http';
import { inject } from '@angular/core';
import { catchError, throwError } from 'rxjs';
import { API_BASE_URL } from './config';
import { SessionEvents } from '../auth/session-events';
import { HTTP_STATUS } from '../constants/ui.constants';

export const EXPECTED_UNAUTHENTICATED = new HttpContextToken(() => false);
export const apiInterceptor: HttpInterceptorFn = (request, next) => {
  const base = inject(API_BASE_URL);
  const sessions = inject(SessionEvents);
  if (!request.url.startsWith(base + '/')) return next(request);
  return next(request.clone({ withCredentials: true })).pipe(
    catchError((error: unknown) => {
      if (
        error instanceof HttpErrorResponse &&
        error.status === HTTP_STATUS.UNAUTHORIZED &&
        !request.context.get(EXPECTED_UNAUTHENTICATED)
      )
        sessions.invalidate();
      return throwError(() => error);
    }),
  );
};
