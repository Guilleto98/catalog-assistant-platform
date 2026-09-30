import { DatePipe } from '@angular/common';
import { Component, computed, input } from '@angular/core';
import { Message } from '../../../api/contracts';
import { UiEventRenderer } from './events/ui-event-renderer';
import { MESSAGE_ROLE } from '../../../core/constants/ui.constants';

@Component({
  selector: 'app-message-bubble',
  imports: [DatePipe, UiEventRenderer],
  template: ` <article
    class="message"
    [class.user-message]="message().role === messageRole.USER"
    [class.system-message]="message().role === messageRole.SYSTEM_EVENT"
  >
    <header>
      @if (message().role !== messageRole.USER) {
        <span class="message-avatar">
          @if (message().role === messageRole.ASSISTANT) {
            <img src="/brand/agrolink-symbol-smooth-3d.svg" alt="" />
          } @else {
            ·
          }
        </span>
      }
      <strong>{{
        message().role === messageRole.USER
          ? 'Vos'
          : message().role === messageRole.ASSISTANT
            ? 'Asistente de artículos'
            : 'Actividad'
      }}</strong>
      <time [attr.datetime]="message().createdAt">{{ message().createdAt | date: 'HH:mm' }}</time>
    </header>
    @if (message().text) {
      <p class="message-text">{{ message().text }}</p>
    }
    @for (attachment of message().attachments; track attachment.id) {
      <p class="attachment-ref">{{ attachment.filename }} · {{ attachment.status }}</p>
    }
    @for (event of events(); track event.id) {
      <app-ui-event-renderer [event]="event" />
    }
  </article>`,
})
export class MessageBubble {
  readonly messageRole = MESSAGE_ROLE;
  readonly message = input.required<Message>();
  readonly events = computed(() =>
    [...this.message().uiEvents].sort((a, b) => a.sequence - b.sequence),
  );
}
