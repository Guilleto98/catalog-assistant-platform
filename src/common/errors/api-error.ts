import { HttpException, HttpStatus } from '@nestjs/common';

export class ApiError extends HttpException {
  constructor(code: string, message: string, status: HttpStatus, details: object = {}) {
    super({ error: { code, message, details } }, status);
  }
}
