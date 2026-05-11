import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { environment } from '../../../environments/environment';
import { WorkflowService } from '../../services/workflow.service';
import { UploadService } from '../../services/upload.service';
import { FileUtils } from '../../utils/file.utils';
import { UploadResponse } from '../../models/api/upload.model.api';
import { AppLoaderComponent } from '../ui/app-loader/app-loader.component';
import { HistoryPanelComponent } from './history-panel/history-panel.component';
import { TutorialService } from '../../services/tutorial.service';
import { OnboardingOverlayComponent } from '../ui/onboarding-overlay/onboarding-overlay.component';

type DownloadState = 'idle' | 'downloading' | 'done' | 'error';

@Component({
  selector: 'app-file-upload',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    AppLoaderComponent,
    HistoryPanelComponent,
    OnboardingOverlayComponent,
  ],
  templateUrl: './file-upload.component.html',
  styleUrls: ['./file-upload.component.css'],
})
export class FileUploadComponent implements OnInit {
  isDragging = false;
  file: File | null = null;
  uploadProgress = 0;

  isUploading = false;
  isProcessing = false;

  // New Download State Logic
  sampleDownloadState: DownloadState = 'idle';
  sampleDownloadProgress = 0;

  showFileStructureLink = false;
  showStructureModal = false;

  errorMessage = '';
  sampleRate: number | null = null;

  manualFilePath: string = '';
  showOnboarding = false;

  isHistoryCollapsed = false;
  selectedHistoryFile: any = null;

  // Modal state
  showPromptTemplateModal = false;

  // User inputs
  userColumnNames = '';
  userFileFormat = 'CSV';
  userCategoryValues = '';
  userExtraNotes = '';

  // Prompt state
  generatedPrompt = '';
  promptCopied = false;

  readonly sampleRateMin = 20;
  readonly sampleRateMax = 3000;
  readonly maxFileSize = environment.maxFileSize;
  readonly allowedFileTypes = environment.allowedFileTypes;

  constructor(
    private router: Router,
    private workflowService: WorkflowService,
    private uploadService: UploadService,
    private tutorialService: TutorialService,
  ) { }

  ngOnInit(): void {
    this.tutorialService.showOnboarding$.subscribe(
      (show) => (this.showOnboarding = show),
    );
  }

  onOnboardingClosed(): void {
    this.tutorialService.markOnboardingSeen();
  }

  toggleHistoryPanel(): void {
    this.isHistoryCollapsed = !this.isHistoryCollapsed;
  }

  showNotification(message: string, isSuccess: boolean = true): void {
    const notification = document.createElement('div');
    const bgColor = isSuccess ? 'bg-green-500' : 'bg-red-500';
    const icon = isSuccess ? 'check_circle' : 'error_outline';

    notification.className = `fixed top-4 right-4 ${bgColor} text-white px-4 py-2 rounded-lg shadow-lg z-[9999] transition-all duration-300 flex items-center gap-2`;
    notification.innerHTML = `<i class="material-icons text-sm">${icon}</i> <span class="text-sm font-medium">${message}</span>`;
    document.body.appendChild(notification);

    setTimeout(() => {
      notification.style.opacity = '0';
      setTimeout(() => notification.remove(), 300);
    }, 3000);
  }

  onHistoryFileSelected(fileDetails: any): void {
    this.selectedHistoryFile = fileDetails;
    const filePath = fileDetails.file_path || fileDetails.filePath;
    this.sampleRate =
      fileDetails.sampling_rate || fileDetails.samplingRate || this.sampleRate;

    if (filePath) {
      this.uploadHistoryPath(filePath);
    } else {
      this.showNotification(
        'Cannot process history file: File path is missing.',
        false,
      );
    }
  }

  uploadHistoryPath(filePath: string): void {
    this.errorMessage = '';
    this.showFileStructureLink = false;
    this.isUploading = true;
    this.uploadProgress = 0;

    this.uploadService.uploadFile(filePath, this.sampleRate!).subscribe({
      next: (event: number | UploadResponse) => {
        if (typeof event === 'number') {
          this.uploadProgress = event;
          if (event === 100) this.isProcessing = true;
        } else {
          this.showNotification(`Loaded: ${event.filename}`);

          const extractedFileName =
            filePath.split('\\').pop()?.split('/').pop() || 'history_file.csv';
          const dummyFile = new File([''], extractedFileName, {
            type: 'text/csv',
          });

          this.workflowService.clearWorkflow();
          sessionStorage.clear();

          this.workflowService.setUploadedFile(dummyFile);
          this.workflowService.setSamplingRate(this.sampleRate!);
          this.workflowService.setUploadedFileId(event.file_id);
          this.workflowService.setUploadedFileNameSubject(event.filename);

          this.isUploading = false;
          this.isProcessing = false;
          this.uploadProgress = 100;

          this.router.navigate(['config']);
        }
      },
      error: (err) => {
        this.isUploading = false;
        this.isProcessing = false;
        this.showNotification(
          'This history file may have been moved or deleted.',
          false
        );
        console.error('History upload error:', err);
      },
    });
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    this.isDragging = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    this.isDragging = false;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    this.isDragging = false;
    const droppedFile = event.dataTransfer?.files[0];
    if (droppedFile) this.processFile(droppedFile);
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const selectedFile = input.files?.[0];
    if (selectedFile) this.processFile(selectedFile);
  }

  processFile(selectedFile: File): void {
    this.errorMessage = '';

    if (!FileUtils.isValidExtension(selectedFile, this.allowedFileTypes)) {
      const ext = selectedFile.name.split('.').pop() || 'unknown';
      this.errorMessage = `Unsupported file format: .${ext}. Supported: ${this.allowedFileTypes.join(', ')}`;
      this.file = null;
      return;
    }

    this.file = selectedFile;
  }

  onNext(): void {
    this.uploadProcess('config');
  }

  uploadProcess(navigateTo: string): void {
    this.errorMessage = '';
    this.showFileStructureLink = false;

    if (!this.file) {
      this.errorMessage = 'Please select a file';
      return;
    }

    if (
      this.sampleRate === null ||
      this.sampleRate < this.sampleRateMin ||
      this.sampleRate > this.sampleRateMax
    ) {
      this.errorMessage = `Sample rate must be between ${this.sampleRateMin} Hz and ${this.sampleRateMax} Hz`;
      return;
    }

    this.isUploading = true;

    this.uploadService.uploadFile(this.file, this.sampleRate).subscribe({
      next: (event: number | UploadResponse) => {
        if (typeof event === 'number') {
          this.uploadProgress = event;
          if (event === 100) this.isProcessing = true;
        } else {
          console.log('Upload response:', event);
          this.workflowService.clearWorkflow();
          sessionStorage.clear();
          this.workflowService.setUploadedFile(this.file!);
          this.workflowService.setSamplingRate(this.sampleRate!);
          this.workflowService.setUploadedFileId(event.file_id);
          this.workflowService.setUploadedFileNameSubject(event.filename);

          this.isUploading = false;
          this.isProcessing = false;
          this.uploadProgress = 100;

          this.router.navigate([navigateTo]);
        }
      },
      error: (err) => {
        this.isUploading = false;
        this.isProcessing = false;

        // Extract detailed error message from backend
        let detailedError =
          'The uploaded file has an invalid structure. Please check your file and try again.';

        if (err.error && err.error.detail) {
          detailedError = err.error.detail;
        } else if (err.message) {
          detailedError = err.message;
        }

        // Show specific error based on the message
        if (detailedError.includes('decimal values')) {
          this.errorMessage =
            '❌ Invalid file: trial_id contains decimal values (e.g., 1.0, 1.1). All trial IDs must be integers.';
        } else if (detailedError.includes('Duplicate trial')) {
          this.errorMessage =
            '❌ Invalid file: Duplicate trial combinations found. Each (subject, session, label, category, trial_id) must be unique.';
        } else if (detailedError.includes('inconsistent rows')) {
          this.errorMessage =
            '❌ Invalid file: Trials have different lengths. All trials must have the same number of time points.';
        } else if (detailedError.includes('Missing required columns')) {
          this.errorMessage = `❌ Invalid file: ${detailedError}`;
        } else {
          this.errorMessage = detailedError;
        }

        this.showFileStructureLink = true;
        console.error('Upload error:', err);
      },
    });
  }

  // NEW: Manual Path Upload Logic (TESTING PURPOSES ONLY)
  uploadManualPath(): void {
    this.errorMessage = '';
    this.showFileStructureLink = false;

    if (!this.manualFilePath.trim()) {
      this.errorMessage = 'Please enter a manual file path';
      return;
    }

    if (
      this.sampleRate === null ||
      this.sampleRate < this.sampleRateMin ||
      this.sampleRate > this.sampleRateMax
    ) {
      this.errorMessage = `Sample rate must be between ${this.sampleRateMin} Hz and ${this.sampleRateMax} Hz`;
      return;
    }

    this.isUploading = true;

    this.uploadService
      .uploadFile(this.manualFilePath.trim(), this.sampleRate)
      .subscribe({
        next: (event: number | UploadResponse) => {
          if (typeof event === 'number') {
            this.uploadProgress = event;
            if (event === 100) this.isProcessing = true;
          } else {
            console.log('Manual Upload response:', event);

            // Hack to prevent Angular from crashing: Create a dummy File object
            // because the WorkflowService expects a real file.
            const extractedFileName =
              this.manualFilePath.split('\\').pop()?.split('/').pop() ||
              'manual_file.csv';
            const dummyFile = new File([''], extractedFileName, {
              type: 'text/csv',
            });

            this.workflowService.clearWorkflow();
            sessionStorage.clear();
            this.workflowService.setUploadedFile(dummyFile);
            this.workflowService.setSamplingRate(this.sampleRate!);
            this.workflowService.setUploadedFileId(event.file_id);
            this.workflowService.setUploadedFileNameSubject(event.filename);

            this.isUploading = false;
            this.isProcessing = false;
            this.uploadProgress = 100;

            this.router.navigate(['config']);
          }
        },
        error: (err) => {
          this.isUploading = false;
          this.isProcessing = false;
          this.errorMessage = err.message;
        },
      });
  }

  getFileSize(): string {
    return this.file ? FileUtils.getFileSize(this.file) : '0 MB';
  }

  // --- Dynamic Sample Download Logic ---

  get sampleDownloadLabel(): string {
    switch (this.sampleDownloadState) {
      case 'downloading': return 'Downloading...';
      case 'done': return 'Saved!';
      case 'error': return 'Failed — retry';
      default: return 'Download Sample CSV';
    }
  }

  get sampleDownloadIcon(): string {
    switch (this.sampleDownloadState) {
      case 'downloading': return 'hourglass_top';
      case 'done': return 'check_circle';
      case 'error': return 'error_outline';
      default: return 'download';
    }
  }

  downloadSampleCSV(): void {
    if (this.sampleDownloadState === 'downloading') return;

    this.sampleDownloadState = 'downloading';
    this.sampleDownloadProgress = 0;

    const progressInterval = setInterval(() => {
      if (this.sampleDownloadProgress < 85) this.sampleDownloadProgress += 5;
    }, 120);

    this.uploadService.downloadSampleFile().subscribe({
      next: (blob) => {
        clearInterval(progressInterval);
        this.sampleDownloadProgress = 100;

        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'sample_eeg.csv';
        a.click();
        window.URL.revokeObjectURL(url);

        this.sampleDownloadState = 'done';
        setTimeout(() => {
          this.sampleDownloadState = 'idle';
          this.sampleDownloadProgress = 0;
        }, 3000);
      },
      error: (err) => {
        clearInterval(progressInterval);
        console.error('Download sample error:', err);
        this.sampleDownloadState = 'error';
        setTimeout(() => {
          this.sampleDownloadState = 'idle';
          this.sampleDownloadProgress = 0;
        }, 3000);
      },
    });
  }

  // --- Modal Logic ---

  openStructureModal(): void {
    this.showStructureModal = true;
    this.showFileStructureLink = false;
    this.closePromptTemplateModal();
    if (this.errorMessage) this.errorMessage = '';
  }

  closeStructureModal(): void {
    this.showStructureModal = false;
    this.showFileStructureLink = false;
  }

  openPromptTemplateModal() {
    this.showPromptTemplateModal = true;
    this.generatePrompt();
  }

  closePromptTemplateModal() {
    this.showPromptTemplateModal = false;
    this.promptCopied = false;
  }

  generatePrompt() {
    const cols = this.userColumnNames.trim() || '[describe your columns here]';
    const fmt = this.userFileFormat || 'CSV';
    const cats = this.userCategoryValues.trim();
    const notes = this.userExtraNotes.trim();

    this.generatedPrompt = `I have EEG data in ${fmt} format that I need to convert to a specific structure for an analysis app.

MY CURRENT STRUCTURE:
Columns: ${cols}${cats ? `\nCategory/condition values I use: ${cats}` : ''}${notes ? `\nAdditional details: ${notes}` : ''}

TARGET STRUCTURE REQUIRED (one row per time point per trial):
- subject_id       → unique integer or string per participant
- session_id       → session number (integer)
- trial_id         → trial number as a whole integer (no decimals)
- category         → must be exactly the string 'motor' or 'imagery'
- time_index       → integer index of the time point within the trial (0, 1, 2, ...)
- channel_1, channel_2, ... channel_N  → one column per EEG channel, named channel_1 through channel_N
- labels           → (optional) one consistent label value per trial

VALIDATION RULES the output must pass:
1. No duplicate time_index within the same (subject_id, session_id, trial_id) group.
2. Every trial must have the same number of rows (same number of time points).
3. Each trial must have exactly one category value.
4. trial_id must be whole integers only.
5. At least one column named channel_*.

Please write a Python script (using pandas) that reads my data and outputs a CSV matching the target structure. Include comments explaining each transformation step.`;
  }

  copyPrompt() {
    navigator.clipboard.writeText(this.generatedPrompt).then(() => {
      this.promptCopied = true;
      setTimeout(() => (this.promptCopied = false), 2500);
    });
  }
}