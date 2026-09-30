import { ArgumentsHost, Catch, ExceptionFilter, HttpException, HttpStatus } from '@nestjs/common';
import type { Response } from 'express';
import { API_ERROR_CODES } from '../constants/api.constants';

@Catch()
export class ApiExceptionFilter implements ExceptionFilter {
  catch(exception: unknown, host: ArgumentsHost): void {
    const response = host.switchToHttp().getResponse<Response>();
    if (exception instanceof HttpException) {
      const status = exception.getStatus();
      const payload = exception.getResponse();
      if (
        typeof payload === 'object' &&
        payload !== null &&
        'error' in payload &&
        typeof payload.error === 'object'
      ) {
        response.status(status).json(payload);
        return;
      }
      const message = typeof payload === 'string' ? payload : 'Request validation failed';
      response
        .status(status)
        .json({ error: { code: API_ERROR_CODES.VALIDATION_ERROR, message, details: payload } });
      return;
    }
    response.status(HttpStatus.INTERNAL_SERVER_ERROR).json({
      error: {
        code: API_ERROR_CODES.INTERNAL_ERROR,
        message: 'An unexpected error occurred',
        details: {},
      },
    });
  }
}
