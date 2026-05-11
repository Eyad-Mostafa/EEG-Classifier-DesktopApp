import { Component, OnInit, Output, EventEmitter, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { UploadService } from '../../../services/upload.service';
import { UploadHistoryItem } from '../../../models/api/upload.model.api';
import { WorkflowService } from '../../../services/workflow.service';
import { ConfirmDialogComponent } from "../../ui/confirm-dialog/confirm-dialog.component";

@Component({
  selector: 'app-history-panel',
  standalone: true,
  imports: [CommonModule, FormsModule, ConfirmDialogComponent],
  templateUrl: './history-panel.component.html',
})
export class HistoryPanelComponent implements OnInit {

  @Input() isCollapsed: boolean = false;
  @Output() toggleCollapse = new EventEmitter<void>();
  @Output() fileSelected = new EventEmitter<UploadHistoryItem>();

  files: UploadHistoryItem[] = [];
  selectedFileId: string | null = null;
  expandedFileId: string | null = null;

  // --- Deletion State Variables ---
  fileToDelete: UploadHistoryItem | null = null;
  showDeleteConfirmForFile: boolean = false;
  showDeleteConfirmAllhistory: boolean = false;
  isDeletingHistory: boolean = false;

  constructor(
    private uploadService: UploadService,
    private workFlowService: WorkflowService
  ) { }

  ngOnInit(): void {
    this.loadHistory();
  }

  loadHistory(): void {
    this.uploadService.getUploadHistory().subscribe(files => {
      this.files = files;
    });
  }

  togglePanel(): void {
    this.toggleCollapse.emit();
  }

  toggleFileExpand(fileId: string, event: Event): void {
    event.stopPropagation();
    this.expandedFileId = this.expandedFileId === fileId ? null : fileId;
  }

  selectFile(file: UploadHistoryItem, event: Event): void {
    event.stopPropagation(); 
    this.selectedFileId = file.file_id;
    this.fileSelected.emit(file);
  }

  formatDate(date: string): string {
    const d = new Date(date);
    const now = new Date();

    const startOfToday = new Date(now.getFullYear(), now.getMonth(), now.getDate());
    const startOfDate = new Date(d.getFullYear(), d.getMonth(), d.getDate());

    const diffDays = Math.floor(
      (startOfToday.getTime() - startOfDate.getTime()) / (1000 * 60 * 60 * 24)
    );

    const time = d.toLocaleTimeString([], {
      hour: '2-digit',
      minute: '2-digit',
    });

    if (diffDays === 0) return `Today at ${time}`;
    if (diffDays === 1) return `Yesterday at ${time}`;
    if (diffDays < 7) return `${diffDays} days ago at ${time}`;

    return `${d.toLocaleDateString('en-GB', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    })} at ${time}`;
  }

  // --- Single File Deletion Methods ---

  openDeleteFileModal(file: UploadHistoryItem, event: Event): void {
    event.stopPropagation(); // Prevents the file card from expanding/selecting
    this.fileToDelete = file;
    this.showDeleteConfirmForFile = true;
  }

  closeDeleteFileModal(): void {
    this.fileToDelete = null;
    this.showDeleteConfirmForFile = false;
  }

  executeDeleteFile(): void {
    if (!this.fileToDelete) return;
    
    this.isDeletingHistory = true;
    this.uploadService.deleteHistoryFile(this.fileToDelete.file_id).subscribe({
      next: () => {
        this.isDeletingHistory = false;
        this.selectedFileId = this.workFlowService.getUploadedFileId();
        if (this.selectedFileId === this.fileToDelete?.file_id) {
          this.workFlowService.clearWorkflow();
        }
        this.fileToDelete = null;
        this.loadHistory();
      },
      error: (err) => {
        console.error('Failed to delete file:', err);
        this.isDeletingHistory = false;
        this.fileToDelete = null;
      }
    });
  }

  openPanelAndExpandFile(fileId: string, event: Event): void {
    event.stopPropagation();
    
    this.expandedFileId = fileId;
    
    if (this.isCollapsed) {
      this.toggleCollapse.emit();
    }
  }

  // --- Delete All History Methods ---

  openDeleteAllModal(event: Event): void {
    event.stopPropagation();
    this.showDeleteConfirmAllhistory = true;
  }

  closeDeleteAllModal(): void {
    this.showDeleteConfirmAllhistory = false;
  }

  executeDeleteHistory(): void {
    this.isDeletingHistory = true;
    this.uploadService.deleteAllHistory().subscribe({
      next: () => {
        this.isDeletingHistory = false;
        this.showDeleteConfirmAllhistory = false;
        this.selectedFileId = null;
        this.workFlowService.clearWorkflow();
        this.loadHistory();
      },
      error: (err) => {
        console.error('Failed to clear all history:', err);
        this.isDeletingHistory = false;
        this.showDeleteConfirmAllhistory = false;
      }
    });
  }
}