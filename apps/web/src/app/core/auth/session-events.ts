import { Injectable, signal } from '@angular/core';
import { SESSION_REASON, STATE_POLICY } from '../constants/ui.constants';

/** Decouples the HTTP interceptor from AuthService and chat state. */
@Injectable({ providedIn: 'root' })
export class SessionEvents {
  readonly revision = signal(0);
  reason: (typeof SESSION_REASON)[keyof typeof SESSION_REASON] = SESSION_REASON.EXPIRED;
  invalidate(
    reason: (typeof SESSION_REASON)[keyof typeof SESSION_REASON] = SESSION_REASON.EXPIRED,
  ): void {
    this.reason = reason;
    this.revision.update((value) => value + STATE_POLICY.REVISION_INCREMENT);
  }
}
