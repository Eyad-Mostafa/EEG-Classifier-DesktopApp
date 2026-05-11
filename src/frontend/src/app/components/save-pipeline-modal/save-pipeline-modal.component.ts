import { Component, EventEmitter, Input, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';

@Component({
    selector: 'app-save-pipeline-modal',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './save-pipeline-modal.component.html',
    styleUrls: ['./save-pipeline-modal.component.css']
})
export class SavePipelineModalComponent {
    @Input() currentFileName: string | null = null;
    @Output() save = new EventEmitter<{ name: string; type: 'global' | 'file-specific'; notes: string }>();
    @Output() close = new EventEmitter<void>();

    pipelineName: string = '';
    pipelineType: 'global' | 'file-specific' = 'global';
    notes: string = '';
    showError: boolean = false;
    isSaving: boolean = false;  // ✅ ADD THIS

    onSave(): void {
        if (!this.pipelineName.trim()) {
            this.showError = true;
            return;
        }

        // ✅ Prevent multiple saves
        if (this.isSaving) return;

        this.isSaving = true;
        this.save.emit({
            name: this.pipelineName.trim(),
            type: this.pipelineType,
            notes: this.notes.trim()
        });

        // ✅ Reset after emit (parent will close modal)
        setTimeout(() => {
            this.isSaving = false;
        }, 500);
    }

    onClose(): void {
        this.close.emit();
    }
}