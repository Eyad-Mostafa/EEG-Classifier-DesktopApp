import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { PipelineService } from '../../../services/pipeline.service';
import { PipelineSummary, SavedPipeline } from '../../../models/pipeline.model';
import { ConfirmDialogComponent } from "../../ui/confirm-dialog/confirm-dialog.component";

@Component({
    selector: 'app-pipeline-panel',
    standalone: true,
    imports: [CommonModule, FormsModule, ConfirmDialogComponent],
    templateUrl: './pipeline-panel.component.html',
    styleUrls: ['./pipeline-panel.component.css']
})
export class PipelinePanelComponent implements OnInit {
    @Input() currentConfigId: string | null = null;
    @Input() currentFileName: string | null = null;
    @Output() loadPipeline = new EventEmitter<SavedPipeline>();
    @Output() close = new EventEmitter<void>();

    activeTab: 'global' | 'file-specific' = 'global';
    globalPipelines: PipelineSummary[] = [];
    fileSpecificPipelines: PipelineSummary[] = [];
    expandedPipelineId: string | null = null;
    isLoading = false;
    showDeleteConfirm = false;
    isDeletingHistory: boolean = false;
    deleteCount = 0;
    pendingDeletePipelineId: string | null = null;
    showDeletePipelineConfirm = false;

    constructor(private pipelineService: PipelineService) { }

    async ngOnInit(): Promise<void> {
        console.log('PipelinePanel initialized with configId:', this.currentConfigId);
        await this.loadPipelines();
    }

    async loadPipelines(): Promise<void> {
        this.isLoading = true;

        try {
            if (this.activeTab === 'global') {
                this.globalPipelines = await this.pipelineService.getPipelineSummaries('global');
                console.log(`Loaded ${this.globalPipelines.length} global pipelines:`, this.globalPipelines);
            } else if (this.activeTab === 'file-specific') {
                if (!this.currentConfigId) {
                    console.warn('⚠️ No config ID provided for file-specific pipelines');
                    this.fileSpecificPipelines = [];
                } else {
                    console.log(`Calling getPipelineSummaries with configId: ${this.currentConfigId}`);
                    this.fileSpecificPipelines = await this.pipelineService.getPipelineSummaries('file-specific', this.currentConfigId);
                    console.log(`Loaded ${this.fileSpecificPipelines.length} file-specific pipelines:`, this.fileSpecificPipelines);
                }
            }
        } catch (error) {
            console.error('Failed to load pipelines:', error);
        } finally {
            this.isLoading = false;
        }
    }

    async onLoadPipeline(pipelineId: string): Promise<void> {
        console.log('Load pipeline clicked with ID:', pipelineId);

        if (!pipelineId) {
            console.error('No pipeline ID provided');
            return;
        }

        try {
            const pipeline = await this.pipelineService.loadPipeline(pipelineId);
            console.log('Pipeline loaded from service:', pipeline);

            if (pipeline) {
                console.log('Emitting pipeline to parent:', pipeline);
                this.loadPipeline.emit(pipeline);
            } else {
                console.error('Pipeline not found with ID:', pipelineId);
                alert('Pipeline not found');
            }
        } catch (error) {
            console.error('Failed to load pipeline:', error);
            alert('Failed to load pipeline: ' + (error as any).message);
        }
    }

    onDeletePipeline(event: Event, pipelineId: string): void {
        event.stopPropagation();
        this.pendingDeletePipelineId = pipelineId;
        this.showDeletePipelineConfirm = true;
    }

    async confirmDeletePipeline(): Promise<void> {
        if (!this.pendingDeletePipelineId) return;
        this.isDeletingHistory = true;
        try {
            await this.pipelineService.deletePipeline(this.pendingDeletePipelineId);
            await this.loadPipelines();
        } catch (error) {
            console.error('Failed to delete pipeline:', error);
        } finally {
            this.isDeletingHistory = false;
            this.showDeletePipelineConfirm = false;
            this.pendingDeletePipelineId = null;
        }
    }

    toggleExpand(pipelineId: string): void {
        this.expandedPipelineId = this.expandedPipelineId === pipelineId ? null : pipelineId;
    }

    formatDate(date: Date): string {
        return new Date(date).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            year: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        });
    }

    onClose(): void {
        console.log('Closing pipeline panel');
        this.close.emit();
    }


    async onDeleteAllGlobalPipelines(event: Event): Promise<void> {
        event.stopPropagation();
        this.deleteCount = this.globalPipelines.length;
        this.showDeleteConfirm = true;
    }

    async onDeleteAllFileSpecificPipelines(event: Event): Promise<void> {
        event.stopPropagation();
        this.deleteCount = this.fileSpecificPipelines.length;
        this.showDeleteConfirm = true;
    }

    async confirmDeleteAll(): Promise<void> {
        this.isDeletingHistory = true;

        try {
            if (this.activeTab === 'global') {
                // Delete all global pipelines
                const deletePromises = this.globalPipelines.map(p =>
                    this.pipelineService.deletePipeline(p.id)
                );
                await Promise.all(deletePromises);
                this.showDeleteConfirm = false;
                this.isDeletingHistory = false;
                console.log(`Deleted ${this.globalPipelines.length} global pipelines`);
            } else {
                // Delete all file-specific pipelines for current file
                const deletePromises = this.fileSpecificPipelines.map(p =>
                    this.pipelineService.deletePipeline(p.id)
                );
                await Promise.all(deletePromises);
                this.showDeleteConfirm = false;
                this.isDeletingHistory = false;
                console.log(`Deleted ${this.fileSpecificPipelines.length} file-specific pipelines`);
            }

            // Refresh the list
            await this.loadPipelines();
        } catch (error) {
            console.error('Failed to delete all pipelines:', error);
            alert('Failed to delete some pipelines. Check console for details.');
        }
    }
    
}
