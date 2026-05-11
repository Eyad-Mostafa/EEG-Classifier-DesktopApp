import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';

// Services
import { WorkflowService } from '../../services/workflow.service';
import { EegDataService } from '../../services/eeg-data.service';

// Models
import {
  MetadataResponse,
  SubjectSessionTrialsSchema,
  SessionTrialsSchema,
} from '../../models/api/metadata.model.api';
import {
  FilterRequest,
  SubjectTrialsFilter,
  SessionTrialsFilter,
} from '../../models/api/preprocessing.model.api';

import { ConfigHistoryItem } from '../../models/api/config-history.model.api';

import { AppLoaderComponent } from '../ui/app-loader/app-loader.component';
import { RestoreConfigModalComponent } from '../ui/restore-config-modal/restore-config-modal.component';
import { ConfigHistoryPanelComponent } from './history-panel/history-panel.component';

@Component({
  selector: 'app-file-config',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    AppLoaderComponent,
    RestoreConfigModalComponent,
    ConfigHistoryPanelComponent
  ],
  templateUrl: './file-config.component.html',
  styleUrls: [],
})
export class FileConfigComponent implements OnInit {
  uploadedFile: File | null = null;
  fileId: string | null = null;
  uploadedFileName: string | null = null;

  metadata: MetadataResponse | null = null;
  isLoadingMetadata = false;
  errorMessage = '';
  isProcessing = false;

  showRestoreModal = false;
  latestSavedConfig: ConfigHistoryItem | null = null;

  isHistoryCollapsed = false;

  labelValues: Record<string, string> = {};
  channelMapping: Record<string, string> = {};
  selectionState: Record<string, Record<string, Record<string, boolean>>> = {};
  expandedSubjects: Record<string, boolean> = {};
  expandedSessions: Record<string, Record<string, boolean>> = {};
  selectedLabels: Record<string, boolean> = {};
  selectedChannels: Record<string, boolean> = {};



  supportedMontages: string[] = [
    'standard_1020',
    'standard_1005',
    'standard_posture',
    'standard_primed',
    'standard_alphabetic',
    'biosemi32',
    'biosemi128',
    'easycap-M1',
    'easycap-M10',
    'brainproducts-RNP-BA-128'
  ];

  selectedMontage: string = 'standard_1020';

  constructor(
    private router: Router,
    private workflowService: WorkflowService,
    private eegDataService: EegDataService
  ) { }

  ngOnInit(): void {
    this.uploadedFile = this.workflowService.getUploadedFile();
    this.fileId = this.workflowService.getUploadedFileId();
    this.uploadedFileName = this.uploadedFile?.name || null;
    if (!this.fileId) {
      this.router.navigate(['/upload']);
      return;
    }

    this.loadMetadata();
    this.checkLatestSavedConfiguration();
    this.handleNavbar();
  }

  loadMetadata(): void {
    if (!this.fileId) return;

    this.isLoadingMetadata = true;
    this.errorMessage = '';

    this.eegDataService.getFileMetadata(this.fileId).subscribe({
      next: (data: MetadataResponse) => {
        this.metadata = data;
        this.isLoadingMetadata = false;

        const savedState = this.workflowService.getFileConfigUIState();

        if (savedState) {
          this.labelValues = savedState.labelValues || {};
          this.channelMapping = savedState.channelMapping || {};
          this.selectionState = (savedState.selectionState as any) || {};
          this.selectedMontage = savedState.selectedMontage || 'standard_1020';
          this.selectedLabels = savedState.selectedLabels || {};  // ← ADD THIS
          this.selectedChannels = savedState.selectedChannels || {};

          this.ensureLabelKeys(data);
          this.ensureChannelMappingKeys(data);
          this.ensureSelectionStateKeys(data);
          this.initLabelSelection(data);
        } else {
          this.labelValues = {};
          this.channelMapping = {};
          this.selectionState = {};
          this.selectedMontage = 'standard_1020';
          this.selectedLabels = {};

          this.initSelectionState(data);
          this.initChannelMapping(data);
          this.initLabelValues(data);
          this.initLabelSelection(data); 
          this.initChannelSelection(data);

        }

        this.saveState();
      },
      error: (err) => {
        console.error('Failed to load metadata', err);
        this.errorMessage = 'Failed to load file structure.';
        this.isLoadingMetadata = false;
      },
    });
  }

  checkLatestSavedConfiguration(): void {
    if (!this.fileId) return;

    if (this.hasShownRestorePrompt()) {
      this.latestSavedConfig = null;
      this.showRestoreModal = false;
      return;
    }

    this.eegDataService.getFileConfigHistory(this.fileId).subscribe({
      next: (configs) => {
        const data = configs || [];

        if (data.length > 0) {
          this.latestSavedConfig = data[0];
          this.showRestoreModal = true;
          this.markRestorePromptAsShown();
        } else {
          this.latestSavedConfig = null;
          this.showRestoreModal = false;
        }
      },
      error: (err) => {
        console.error('Failed to check latest saved configuration', err);
        this.latestSavedConfig = null;
        this.showRestoreModal = false;
      }
    });
  }

  initLabelValues(data: MetadataResponse): void {
    if (data.labels && data.labels.length > 0) {
      data.labels.forEach(label => {
        const key = String(label);
        if (this.labelValues[key] === undefined) {
          this.labelValues[key] = '';
        }
      });
    }
  }

  initChannelMapping(data: MetadataResponse): void {
    if (data.channels) {
      data.channels.forEach(ch => {
        this.channelMapping[ch] = this.channelMapping[ch] ?? '';
      });
    }
  }

  initSelectionState(data: MetadataResponse): void {
    data.subjects.forEach((subject) => {
      const subjectId = String(subject.subjectId);

      if (!this.selectionState[subjectId]) {
        this.selectionState[subjectId] = {};
      }

      subject.sessions.forEach((session) => {
        const sessionId = String(session.sessionId);

        if (!this.selectionState[subjectId][sessionId]) {
          this.selectionState[subjectId][sessionId] = {};
        }

        session.trials.forEach((trial) => {
          const trialId = String(trial);
          if (this.selectionState[subjectId][sessionId][trialId] === undefined) {
            this.selectionState[subjectId][sessionId][trialId] = true; // Default selected
          }
        });
      });
    });
  }

  ensureChannelMappingKeys(data: MetadataResponse): void {
    data.channels.forEach(ch => {
      if (this.channelMapping[ch] === undefined) {
        this.channelMapping[ch] = '';
      }
    });
  }

  ensureSelectionStateKeys(data: MetadataResponse): void {
    data.subjects.forEach((subject) => {
      const subjectId = String(subject.subjectId);

      if (!this.selectionState[subjectId]) {
        this.selectionState[subjectId] = {};
      }

      subject.sessions.forEach((session) => {
        const sessionId = String(session.sessionId);

        if (!this.selectionState[subjectId][sessionId]) {
          this.selectionState[subjectId][sessionId] = {};
        }

        session.trials.forEach((trial) => {
          const trialId = String(trial);
          // ✅ Only set if undefined (preserve restored values)
          if (this.selectionState[subjectId][sessionId][trialId] === undefined) {
            this.selectionState[subjectId][sessionId][trialId] = true;
          }
        });
      });
    });
  }

  ensureLabelKeys(data: MetadataResponse): void {
    if (data.labels && data.labels.length > 0) {
      data.labels.forEach(label => {
        const key = String(label);
        if (this.labelValues[key] === undefined) {
          this.labelValues[key] = '';
        }
      });
    }
  }

  toggleSubject(subjectId: string): void {
    const sessions = this.selectionState[subjectId];
    if (!sessions) return;

    const isCurrentlyAllSelected = this.isSubjectSelected(subjectId);
    const newState = !isCurrentlyAllSelected;

    Object.keys(sessions).forEach((sessionId) => {
      Object.keys(sessions[sessionId]).forEach((trialId) => {
        sessions[sessionId][trialId] = newState;
      });
    });

    this.saveState();
  }

  toggleSession(subjectId: string, sessionId: string): void {
    if (this.selectionState[subjectId] && this.selectionState[subjectId][sessionId]) {
      const trials = this.selectionState[subjectId][sessionId];
      const isCurrentlyAllSelected = this.isSessionSelected(subjectId, sessionId);
      const newState = !isCurrentlyAllSelected;

      Object.keys(trials).forEach((trialId) => {
        trials[trialId] = newState;
      });
    }
    this.saveState();
  }

  toggleTrial(subjectId: string, sessionId: string, trialId: string): void {
    if (this.selectionState[subjectId]?.[sessionId]?.[trialId] !== undefined) {
      this.selectionState[subjectId][sessionId][trialId] =
        !this.selectionState[subjectId][sessionId][trialId];
    }
    this.saveState();
  }

  toggleSubjectDropdown(subjectId: string, event: Event): void {
    event.stopPropagation();

    this.expandedSubjects[subjectId] = !this.expandedSubjects[subjectId];
  }

  isSubjectExpanded(subjectId: string): boolean {
    return !!this.expandedSubjects[subjectId];
  }

  toggleSessionDropdown(subjectId: string, sessionId: string, event: Event): void {
    event.stopPropagation();

    if (!this.expandedSessions[subjectId]) {
      this.expandedSessions[subjectId] = {};
    }

    this.expandedSessions[subjectId][sessionId] =
      !this.expandedSessions[subjectId][sessionId];
  }

  isSessionExpanded(subjectId: string, sessionId: string): boolean {
    return !!this.expandedSessions[subjectId]?.[sessionId];
  }

  isSubjectSelected(subjectId: string): boolean {
    const sessions = this.selectionState[subjectId];
    if (!sessions) return false;

    let totalTrials = 0;
    let selectedTrials = 0;

    Object.values(sessions).forEach((session) => {
      Object.values(session).forEach((isSelected) => {
        totalTrials++;
        if (isSelected) selectedTrials++;
      });
    });

    return totalTrials > 0 && totalTrials === selectedTrials;
  }

  isSubjectIndeterminate(subjectId: string): boolean {
    const sessions = this.selectionState[subjectId];
    if (!sessions) return false;

    let totalTrials = 0;
    let selectedTrials = 0;

    Object.values(sessions).forEach((session) => {
      Object.values(session).forEach((isSelected) => {
        totalTrials++;
        if (isSelected) selectedTrials++;
      });
    });

    return selectedTrials > 0 && selectedTrials < totalTrials;
  }

  isSessionSelected(subjectId: string, sessionId: string): boolean {
    const trials = this.selectionState[subjectId]?.[sessionId];
    if (!trials) return false;

    const trialValues = Object.values(trials);
    return trialValues.length > 0 && trialValues.every(v => v === true);
  }

  isSessionIndeterminate(subjectId: string, sessionId: string): boolean {
    const trials = this.selectionState[subjectId]?.[sessionId];
    if (!trials) return false;

    const trialValues = Object.values(trials);
    const hasTrue = trialValues.some(v => v === true);
    const hasFalse = trialValues.some(v => v === false);

    return hasTrue && hasFalse;
  }

  processAndNavigate(targetRoute: string): void {
    if (!this.fileId || !this.metadata) return;

    const cleanChannelMap: Record<string, string> = {};
    Object.entries(this.channelMapping).forEach(([key, value]) => {
      // Only include selected channels
      if (this.selectedChannels[key] && value && value.trim() !== '') {
        cleanChannelMap[key] = value.trim();
      } else if (this.selectedChannels[key] && (!value || value.trim() === '')) {
        // Keep original name if selected but not renamed
        cleanChannelMap[key] = key;
      }
    });

    const selectedSubjects: SubjectTrialsFilter[] = this.metadata.subjects
      .map((subject) => {
        const subjectId = String(subject.subjectId);

        const sessions = subject.sessions
          .map((session) => {
            const sessionId = String(session.sessionId);

            const selectedTrials = session.trials
              .map((trial) => String(trial))
              .filter((trialId) => this.selectionState[subjectId]?.[sessionId]?.[trialId]);

            return {
              sessionId: sessionId,
              trials: selectedTrials
            };
          })
          .filter((session) => session.trials.length > 0);

        return {
          subjectId: subjectId,
          sessions: sessions
        };
      })
      .filter((subject) => subject.sessions.length > 0);

    let selectedLabelsPayload: Record<string, number> = {};

    // Only validate labels if the file actually HAS labels
    if (this.metadata.labels && this.metadata.labels.length > 0) {
      selectedLabelsPayload = {};
      Object.keys(this.selectedLabels).forEach(label => {
        if (this.selectedLabels[label]) {
          const labelNumber = parseInt(label, 10);
          if (!isNaN(labelNumber)) {
            // Use the user-typed name as key, fallback to the number string if none provided
            const labelName = (this.labelValues?.[label] ?? '').trim();
            const key = labelName !== '' ? labelName : label;
            selectedLabelsPayload[key] = labelNumber;
          }
        }
      });

      if (Object.keys(selectedLabelsPayload).length === 0) {
        this.errorMessage = '⚠️ Please select at least one label to proceed.';
        return;
      }
    } else {
      // ✅ IMPORTANT: Send empty OBJECT, not empty array
      selectedLabelsPayload = {};
    }

    const payload: FilterRequest = {
      labels: selectedLabelsPayload,
      subjects: selectedSubjects,
      channels: cleanChannelMap,
      selected_channels: this.selectedChannels,  // ← ADD THIS
      montage: this.selectedMontage,
    };

    if (payload.subjects.length === 0) {
      this.errorMessage = '⚠️ Please select at least one session data to proceed.';
      return;
    }

    // Log the full payload
    console.log('Full payload:', JSON.stringify(payload, null, 2));

    this.isProcessing = true;
    this.errorMessage = '';

    this.eegDataService.filterFile(this.fileId, payload).subscribe({
      next: (response) => {
        this.workflowService.clearProcessingResults();
        this.workflowService.setConfiguredFileId(response.tempFileId);

        this.workflowService.updateNavState({
          '/preprocess': false,
          '/analysis': false,
          '/visualization': false,
          '/ai-models': false
        });

        this.isProcessing = false;

        const route = targetRoute.startsWith('/')
          ? targetRoute
          : `/${targetRoute}`;
        this.router.navigate([route]);
      },
      error: (err) => {
        console.error('Filter error details:', err);
        if (err.error) {
          console.error('Error response:', err.error);
          this.errorMessage = err.error?.detail || '❌ Failed to process data selection. Please try again.';
        } else {
          this.errorMessage = '❌ Failed to process data selection. Please try again.';
        }
        this.isProcessing = false;
      },
    });
  }

  getLabelNumber(labelName: string): number {
    // Convert the label string to a number
    const num = parseInt(labelName, 10);
    return isNaN(num) ? 0 : num;
  }

  onPrevious(): void {
    this.router.navigate(['/upload']);
  }

  handleNavbar(): void {
  }

  handleRestoreDecision(applyPrevious: boolean): void {
    this.showRestoreModal = false;

    if (applyPrevious && this.latestSavedConfig) {
      this.onHistoryConfigurationSelected(this.latestSavedConfig);
    }

    this.saveState();
  }

  toggleHistoryPanel(): void {
    this.isHistoryCollapsed = !this.isHistoryCollapsed;
  }

  onHistoryConfigurationSelected(config: ConfigHistoryItem): void {
    if (!this.metadata) return;

    const cfg = config.configuration_json;

    console.log('Restoring config - cfg.subjects:', cfg.subjects);

    // Restore selected labels AND label values
    const restoredSelectedLabels: Record<string, boolean> = {};
    const restoredLabelValues: Record<string, string> = {};

    Object.entries(cfg.labels || {}).forEach(([labelName, labelNumber]) => {
      const numStr = String(labelNumber);
      restoredSelectedLabels[numStr] = true;
      restoredLabelValues[numStr] = labelName;
    });

    this.selectedLabels = restoredSelectedLabels;
    this.labelValues = restoredLabelValues;

    // ========== FIXED: RESTORE SELECTED CHANNELS (Type-Safe) ==========
    const restoredSelectedChannels: Record<string, boolean> = {};

    if (cfg.selected_channels) {
      // Case 1: selected_channels is an ARRAY (old format)
      if (Array.isArray(cfg.selected_channels)) {
        console.log('Restoring channels from array format:', cfg.selected_channels);
        cfg.selected_channels.forEach((channel: any) => {
          const channelName = channel.name || channel.id || channel.label;
          if (channelName && this.metadata!.channels.includes(channelName)) {
            restoredSelectedChannels[channelName] = true;
          }
        });
        // Any channel not in the array defaults to false (not selected)
        this.metadata.channels.forEach(ch => {
          if (restoredSelectedChannels[ch] === undefined) {
            restoredSelectedChannels[ch] = false;
          }
        });
      }
      // Case 2: selected_channels is an OBJECT (new format)
      else if (typeof cfg.selected_channels === 'object' && cfg.selected_channels !== null) {
        console.log('Restoring channels from object format:', cfg.selected_channels);
        // Type-safe iteration over object keys
        const selectedChannelsObj = cfg.selected_channels as Record<string, boolean>;
        Object.keys(selectedChannelsObj).forEach((ch) => {
          if (this.metadata!.channels.includes(ch)) {
            restoredSelectedChannels[ch] = selectedChannelsObj[ch];
          }
        });
      }
    }

    // If no channels were restored, select all channels by default
    if (Object.keys(restoredSelectedChannels).length === 0 && this.metadata.channels.length > 0) {
      console.log('No channel selection found, defaulting to all channels selected');
      this.metadata.channels.forEach(ch => {
        restoredSelectedChannels[ch] = true;
      });
    }

    this.selectedChannels = restoredSelectedChannels;
    console.log('Restored selected channels:', this.selectedChannels);
    // ========== END CHANNEL RESTORATION ==========

    // Restore channels mapping
    const restoredChannels: Record<string, string> = {};
    this.metadata.channels.forEach((ch) => {
      restoredChannels[ch] = cfg.channels?.[ch] ?? '';
    });
    this.channelMapping = restoredChannels;

    // Initialize all trials as false
    const restoredSelection: Record<string, Record<string, Record<string, boolean>>> = {};
    this.metadata.subjects.forEach((subject) => {
      const subjectId = String(subject.subjectId);
      restoredSelection[subjectId] = {};

      subject.sessions.forEach((session) => {
        const sessionId = String(session.sessionId);
        restoredSelection[subjectId][sessionId] = {};

        session.trials.forEach((trial) => {
          restoredSelection[subjectId][sessionId][String(trial)] = false;
        });
      });
    });

    // Restore selections from history
    (cfg.subjects || []).forEach((subject: any) => {
      const subjectId = String(subject.subjectId);

      const firstSession = subject.sessions?.[0];
      const isOldFormat = firstSession && typeof firstSession === 'string';

      if (isOldFormat) {
        const selectedSessions = subject.sessions || [];
        selectedSessions.forEach((sessionId: string) => {
          if (restoredSelection[subjectId] && restoredSelection[subjectId][sessionId]) {
            Object.keys(restoredSelection[subjectId][sessionId]).forEach((trialId) => {
              restoredSelection[subjectId][sessionId][trialId] = true;
            });
          }
        });
      } else {
        const sessions = subject.sessions || [];
        sessions.forEach((session: any) => {
          const sessionId = String(session.sessionId);
          const selectedTrials = session.trials || [];

          if (restoredSelection[subjectId] && restoredSelection[subjectId][sessionId]) {
            selectedTrials.forEach((trialId: string) => {
              if (restoredSelection[subjectId][sessionId][trialId] !== undefined) {
                restoredSelection[subjectId][sessionId][trialId] = true;
              }
            });
          }
        });
      }
    });

    this.selectionState = restoredSelection;
    this.selectedMontage = cfg.montage || 'standard_1020';

    this.ensureLabelKeys(this.metadata);
    this.ensureChannelMappingKeys(this.metadata);

    this.saveState();
    this.metadata = { ...this.metadata };
  }
  
  saveState(): void {
    this.workflowService.setFileConfigUIState({
      labelValues: this.labelValues,
      channelMapping: this.channelMapping,
      selectionState: this.selectionState as any,
      selectedMontage: this.selectedMontage,
      selectedLabels: this.selectedLabels,
      selectedChannels: this.selectedChannels,
      restoreModalSeen: !this.showRestoreModal
    });
  }

  private getRestorePromptKey(): string | null {
    return this.fileId ? `config-restore-prompt-shown:${this.fileId}` : null;
  }

  private hasShownRestorePrompt(): boolean {
    const key = this.getRestorePromptKey();
    return key ? sessionStorage.getItem(key) === 'true' : false;
  }

  private markRestorePromptAsShown(): void {
    const key = this.getRestorePromptKey();
    if (key) {
      sessionStorage.setItem(key, 'true');
    }
  }

  // Add these methods (around line 200)
  toggleLabel(label: string): void {
    this.selectedLabels[label] = !this.selectedLabels[label];
    this.saveState();
  }

  isLabelSelected(label: string): boolean {
    return this.selectedLabels[label] === true;
  }

  initLabelSelection(data: MetadataResponse): void {
    if (data.labels && data.labels.length > 0) {
      data.labels.forEach(label => {
        const key = String(label);
        if (this.selectedLabels[key] === undefined) {
          this.selectedLabels[key] = true; // Default: selected
        }
      });
    }
  }

  selectAllLabels(): void {
    if (!this.metadata?.labels) return;
    this.metadata.labels.forEach(label => {
      this.selectedLabels[String(label)] = true;
    });
    this.saveState();
  }

  toggleChannel(channel: string): void {
  this.selectedChannels[channel] = !this.selectedChannels[channel];
  this.saveState();
}

isChannelSelected(channel: string): boolean {
  return this.selectedChannels[channel] === true;
}

selectAllChannels(): void {
  if (!this.metadata?.channels) return;
  this.metadata.channels.forEach(channel => {
    this.selectedChannels[channel] = true;
  });
  this.saveState();
}

deselectAllChannels(): void {
  if (!this.metadata?.channels) return;
  this.metadata.channels.forEach(channel => {
    this.selectedChannels[channel] = false;
  });
  this.saveState();
}

initChannelSelection(data: MetadataResponse): void {
  if (data.channels && data.channels.length > 0) {
    data.channels.forEach(channel => {
      const key = String(channel);
      if (this.selectedChannels[key] === undefined) {
        this.selectedChannels[key] = true; // Default: all channels selected
      }
    });
  }
  }
  
}
