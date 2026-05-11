import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-restore-config-modal',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './restore-config-modal.component.html', // Pointing to the new file
  styleUrls: []
})
export class RestoreConfigModalComponent {
  @Input() fileName: string = 'Unknown File';
  @Output() decision = new EventEmitter<boolean>();

  onDecision(applyPrevious: boolean): void {
    this.decision.emit(applyPrevious);
  }
}