import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-confirm-dialog',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './confirm-dialog.component.html',
})
export class ConfirmDialogComponent {
  /** Controls visibility */
  @Input() isOpen = false;

  /** Modal title */
  @Input() heading = 'Are you sure?';

  /** Body text — supports a second paragraph via secondaryMessage */
  @Input() message = 'This action cannot be undone.';
  @Input() secondaryMessage = '';

  /** Confirm button label */
  @Input() confirmLabel = 'Confirm';

  /** Show spinner + disabled state on confirm button while parent is processing */
  @Input() isLoading = false;

  /** Emitted when the user clicks confirm */
  @Output() confirmed = new EventEmitter<void>();

  /** Emitted when the user clicks cancel or the backdrop */
  @Output() cancelled = new EventEmitter<void>();
}
