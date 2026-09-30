import { HttpException, HttpStatus } from '@nestjs/common';
import type { ApiErrorCode } from '../constants/api.constants';

export class ApiError extends HttpException {
  constructor(code: ApiErrorCode, message: string, status: HttpStatus, details: object = {}) {
    super({ error: { code, message, details } }, status);
  }
}
