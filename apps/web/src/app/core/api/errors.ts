import { HttpErrorResponse } from '@angular/common/http';
import { HTTP_STATUS } from '../constants/ui.constants';

export function safeError(error: unknown): string {
  if (!(error instanceof HttpErrorResponse)) return 'No se pudo completar la operación.';
  if (error.status === HTTP_STATUS.NETWORK_ERROR)
    return 'No pudimos conectar con el servicio. Verificá la conexión y volvé a intentar.';
  if (error.status === HTTP_STATUS.UNAUTHORIZED)
    return 'La sesión terminó. Iniciá sesión para continuar.';
  if (error.status === HTTP_STATUS.FORBIDDEN)
    return 'No tenés permiso para realizar esta operación.';
  if (error.status === HTTP_STATUS.NOT_FOUND)
    return error.url?.includes('/conversations/')
      ? 'Conversación no encontrada.'
      : 'Recurso no encontrado.';
  if (error.status >= HTTP_STATUS.INTERNAL_SERVER_ERROR)
    return 'El servicio no está disponible temporalmente. Intentá nuevamente más tarde.';
  // Only the API's public error envelope is eligible for display; never stringify raw errors.
  const body: unknown = error.error;
  if (typeof body === 'object' && body !== null && 'error' in body) {
    const detail: unknown = body.error;
    if (
      typeof detail === 'object' &&
      detail !== null &&
      'message' in detail &&
      typeof detail.message === 'string'
    ) {
      return detail.message;
    }
  }
  return 'No se pudo completar la operación.';
}
