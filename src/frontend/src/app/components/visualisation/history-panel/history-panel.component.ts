import { CommonModule } from '@angular/common';
import { Component, EventEmitter, Input, Output } from '@angular/core';
import { ConfirmDialogComponent } from '../../ui/confirm-dialog/confirm-dialog.component';


export interface SavedPlotItem {
  plot_id: string | number;
  file_id?: string | number;
  plot_name: string;
  filter_json: {
    data_type?: 'raw' | 'clean';
    subject?: string | string[];
    session?: string | string[];
    labels?: string[];
    category?: string[];
    channels?: string[];
    montage?: string;
  };
  created_at: string | Date;
}

@Component({
  selector: 'app-history-panel',
  standalone: true,
  imports: [CommonModule, ConfirmDialogComponent],
  templateUrl: './history-panel.component.html',
})
export class HistoryPanelComponent {
  @Input() isOpen = false;
  @Input() currentFileName: string | null = null;
  @Input() savedPlots: SavedPlotItem[] = [];

  @Output() close = new EventEmitter<void>();
  @Output() generatePlot = new EventEmitter<SavedPlotItem>();
  @Output() deletePlot = new EventEmitter<SavedPlotItem>();
  @Output() deleteAllPlots = new EventEmitter<void>(); // ← NEW

  expandedPlotId: number | null = null;

  // ── confirm: single delete ───────────────────────────────────────
  showDeleteConfirm = false;
  pendingDeletePlot: SavedPlotItem | null = null;

  // ── confirm: delete all ──────────────────────────────────────────
  showDeleteAllConfirm = false;

  // ─────────────────────────────────────────────────────────────────

  onClose(): void {
    this.close.emit();
  }

  onGenerate(plot: SavedPlotItem, event?: Event): void {
    event?.stopPropagation();
    this.generatePlot.emit(plot);
    this.onClose();
  }

  // Step 1: open confirm dialog for single delete
  onDelete(plot: SavedPlotItem, event?: Event): void {
    event?.stopPropagation();
    this.pendingDeletePlot = plot;
    this.showDeleteConfirm = true;
  }

  // Step 2: user confirmed single delete → emit to parent
  confirmDelete(): void {
    if (this.pendingDeletePlot) {
      this.deletePlot.emit(this.pendingDeletePlot);
    }
    this.showDeleteConfirm = false;
    this.pendingDeletePlot = null;
    this.expandedPlotId = null;
  }

  cancelDelete(): void {
    this.showDeleteConfirm = false;
    this.pendingDeletePlot = null;
  }

  // Delete all
  onDeleteAll(event?: Event): void {
    event?.stopPropagation();
    this.showDeleteAllConfirm = true;
  }

  confirmDeleteAll(): void {
    this.deleteAllPlots.emit();
    this.showDeleteAllConfirm = false;
  }

  cancelDeleteAll(): void {
    this.showDeleteAllConfirm = false;
  }

  // ─── utils ───────────────────────────────────────────────────────

  toggleExpand(plotId: string | number, event?: Event): void {
    event?.stopPropagation();
    const id = Number(plotId);
    this.expandedPlotId = this.expandedPlotId === id ? null : id;
  }

  formatDate(date: string | Date): string {
    const d = new Date(date);
    if (isNaN(d.getTime())) return '-';
    return d.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  private toArray(value: string | string[] | undefined): string[] {
    if (!value) return [];
    return Array.isArray(value) ? value : [value];
  }

  getFilterSummary(plot: SavedPlotItem): string {
    const f = plot.filter_json;
    const parts: string[] = [];
    if (f?.data_type) parts.push(`Type: ${f.data_type}`);
    if (f?.subject)
      parts.push(`Subject: ${this.toArray(f.subject).join(', ')}`);
    if (f?.session)
      parts.push(`Session: ${this.toArray(f.session).join(', ')}`);
    if (f?.labels?.length) parts.push(`Labels: ${f.labels.join(', ')}`);
    if (f?.category?.length) parts.push(`Category: ${f.category.join(', ')}`);
    if (f?.channels?.length) parts.push(`Channels: ${f.channels.join(', ')}`);
    return parts.length ? parts.join(' | ') : 'No filters';
  }

  getSubjectsCount(plot: SavedPlotItem): number {
    return this.toArray(plot.filter_json?.subject).length;
  }
  getSessionsCount(plot: SavedPlotItem): number {
    return this.toArray(plot.filter_json?.session).length;
  }
  getLabelsCount(plot: SavedPlotItem): number {
    return plot.filter_json?.labels?.length || 0;
  }
  getCategoriesCount(plot: SavedPlotItem): number {
    return plot.filter_json?.category?.length || 0;
  }
  getChannelsCount(plot: SavedPlotItem): number {
    return plot.filter_json?.channels?.length || 0;
  }
  getMontage(plot: SavedPlotItem): string {
    return plot.filter_json?.montage || 'standard_1020';
  }

  trackByPlotId(_: number, item: SavedPlotItem): string | number {
    return item.plot_id ?? _;
  }
}
