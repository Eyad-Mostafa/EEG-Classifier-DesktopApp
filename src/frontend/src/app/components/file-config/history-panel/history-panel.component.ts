import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { EegDataService } from '../../../services/eeg-data.service';
import { ConfigHistoryItem } from '../../../models/api/config-history.model.api';
import { WorkflowService } from '../../../services/workflow.service';
import { ConfirmDialogComponent } from "../../ui/confirm-dialog/confirm-dialog.component";

@Component({
    selector: 'app-config-history-panel',
    standalone: true,
    imports: [CommonModule, FormsModule, ConfirmDialogComponent],
    templateUrl: './history-panel.component.html',
})
export class ConfigHistoryPanelComponent implements OnInit {
    @Input() isCollapsed: boolean = false;
    @Input() fileId: string | null = null;
    @Input() currentFilename: string | null = null;  // ← ADD THIS LINE


    @Output() toggleCollapse = new EventEmitter<void>();
    @Output() configurationSelected = new EventEmitter<ConfigHistoryItem>();

    configurations: ConfigHistoryItem[] = [];
    selectedConfigId: string | null = null;
    expandedConfigId: string | null = null;

    isLoading = false;
    errorMessage = '';

    configToDelete: ConfigHistoryItem | null = null;
    showDeleteConfirmForConfig: boolean = false;
    isDeleting: boolean = false;

    showDeleteAllConfirm: boolean = false;
    isDeletingAll: boolean = false;

    constructor(
        private eegDataService: EegDataService,
        private workflowService: WorkflowService
    ) { }

    ngOnInit(): void {
        this.loadHistory();
    }

    loadHistory(): void {
        if (!this.fileId) {
            this.configurations = [];
            this.isLoading = false;
            this.errorMessage = '';
            return;
        }

        this.isLoading = true;
        this.errorMessage = '';

        this.eegDataService.getFileConfigHistory(this.fileId).subscribe({
            next: (data) => {
                // Convert config_id from number to string for consistent comparison
                this.configurations = (data || []).map(config => ({
                    ...config,
                    config_id: String(config.config_id)
                }));
                this.isLoading = false;
            },
            error: (err) => {
                console.error('Failed to load configuration history', err);
                this.configurations = [];
                this.errorMessage = 'Failed to load configuration history.';
                this.isLoading = false;
            }
        });
    }

    togglePanel(): void {
        this.toggleCollapse.emit();
    }

    toggleConfigExpand(configId: string, event: Event): void {
        event.stopPropagation();
        this.expandedConfigId = this.expandedConfigId === configId ? null : configId;
    }

    selectConfiguration(config: ConfigHistoryItem, event: Event): void {
        event.stopPropagation();

        if (this.isCollapsed) {
            this.togglePanel();
            return;
        }

        this.selectedConfigId = config.config_id;
        this.configurationSelected.emit(config);
        this.workflowService.resetNavStateAfterDeletingAllConfigs();
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

    getSubjectsCount(config: ConfigHistoryItem): number {
        return config.configuration_json.subjects?.length || 0;
    }

    getSessionsCount(config: ConfigHistoryItem): number {
        const subjects = config.configuration_json.subjects;
        if (!subjects || subjects.length === 0) return 0;

        // Check if this config has trials (new format) or just sessions (old format)
        const firstSession = subjects[0]?.sessions?.[0];
        const hasTrials = firstSession && typeof firstSession === 'object' && 'trials' in firstSession;

        if (hasTrials) {
            // New format: count trials
            let totalTrials = 0;
            subjects.forEach((subject: any) => {
                subject.sessions?.forEach((session: any) => {
                    totalTrials += session.trials?.length || 0;
                });
            });
            return totalTrials;
        } else {
            // Old format: count sessions
            return subjects.reduce(
                (sum, subject) => sum + (subject.sessions?.length || 0),
                0
            );
        }
    }

    getLabelsCount(config: ConfigHistoryItem): number {
        return Object.keys(config.configuration_json.labels || {}).length;
    }

    getChannelsCount(config: ConfigHistoryItem): number {
        return Object.keys(config.configuration_json.channels || {}).length;
    }


    getItemLabel(config: ConfigHistoryItem): string {
        try {
            const subjects = config.configuration_json.subjects;
            if (!subjects || subjects.length === 0) return 'Sessions';

            const firstSession = subjects[0]?.sessions?.[0];
            if (firstSession && typeof firstSession === 'object' && 'trials' in firstSession) {
                return 'Trials';
            }
            return 'Sessions';
        } catch (e) {
            return 'Sessions';
        }
    }

    // Add this new method to get display name for config
    getDisplayName(config: ConfigHistoryItem, index: number): string {
        // If we have the current filename, use it for the first config or as base
        if (this.currentFilename) {
            // Remove extension and add "Configuration" suffix
            const nameWithoutExt = this.currentFilename.replace(/\.[^/.]+$/, '');

            // If there are multiple configs for same file, add version number
            if (this.configurations.length > 1) {
                const version = this.configurations.length - index;
                return `${nameWithoutExt} (v${version})`;
            }
            return nameWithoutExt;
        }

        // Fallback to original behavior
        return `Configuration #${config.config_id}`;
    }

    openDeleteConfigModal(config: ConfigHistoryItem, event: Event): void {
        event.stopPropagation();
        this.configToDelete = config;
        this.showDeleteConfirmForConfig = true;
    }

    confirmDeleteConfig(): void {
        if (!this.configToDelete || !this.fileId) return;

        this.isDeleting = true;
        const deletedId = String(this.configToDelete.config_id);
        const activeConfigId = this.workflowService.getConfiguredFileId();
        this.eegDataService
            .deleteSingleFileConfig(this.fileId, String(this.configToDelete.config_id)).subscribe({
                next: () => {
                    this.configurations = this.configurations.filter(
                        c => c.config_id !== this.configToDelete!.config_id
                    );

                    if (this.selectedConfigId === this.configToDelete!.config_id) {
                        this.selectedConfigId = null;
                    }

                    if (this.expandedConfigId === this.configToDelete!.config_id) {
                        this.expandedConfigId = null;
                    }
                    if (activeConfigId === deletedId) {
                        this.workflowService.resetNavStateAfterDeletingAllConfigs();
                    }
                    this.configToDelete = null;
                    this.showDeleteConfirmForConfig = false;
                    this.isDeleting = false;
                },
                error: (err) => {
                    console.error(err);
                    this.errorMessage = 'Failed to delete configuration.';
                    this.configToDelete = null;
                    this.showDeleteConfirmForConfig = false;
                    this.isDeleting = false;
                }
            });
    }

    closeDeleteConfigModal(): void {
        this.configToDelete = null;
    }

    openDeleteAllModal(event: Event): void {
        event.stopPropagation();
        this.showDeleteAllConfirm = true;
    }

    closeDeleteAllModal(): void {
        this.showDeleteAllConfirm = false;
    }

    confirmDeleteAllConfigurations(): void {
        if (!this.fileId) return;

        this.isDeletingAll = true;

        this.eegDataService.deleteFileConfigHistory(this.fileId).subscribe({
            next: () => {
                this.configurations = [];
                this.selectedConfigId = null;
                this.expandedConfigId = null;
                this.workflowService.resetNavStateAfterDeletingAllConfigs();
                this.isDeletingAll = false;
                this.showDeleteAllConfirm = false;
            },
            error: (err) => {
                console.error('Failed to delete configuration history', err);
                this.errorMessage = 'Failed to delete configuration history.';

                this.isDeletingAll = false;
                this.showDeleteAllConfirm = false;
            }
        });
    }
}

