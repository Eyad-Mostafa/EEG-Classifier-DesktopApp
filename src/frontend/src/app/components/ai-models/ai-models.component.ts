import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { WorkflowService } from '../../services/workflow.service';
import { AiModelsService } from '../../services/ai-models.service';
import { AppLoaderComponent } from '../ui/app-loader/app-loader.component';
import { 
  AiModel, 
  PredictionItem, 
  InferenceSummary, 
  FileLabelInfo
} from '../../models/api/ai-models.model';
import { AiModelsTutorialComponent } from '../ai-models-tutorial.component/ai-models-tutorial.component';
import { TutorialService } from '../../services/tutorial.service';

@Component({
  selector: 'app-ai-models',
  standalone: true,
  imports: [CommonModule, FormsModule, AppLoaderComponent, AiModelsTutorialComponent],
  templateUrl: './ai-models.component.html',
  styleUrls: []
})
export class AiModelsComponent implements OnInit {
  showAiTutorial = false;
  tutorialGhostBarActive = false;

  models: AiModel[] = [];
  selectedModelId: string | null = null;
  uploadedFileName: string = '';
  
  isProcessing = false;
  errorMessage = '';
  
  predictionResults: PredictionItem[] | null = null; 
  inferenceSummary: InferenceSummary | null = null;
  currentResultId: string | null = null;
  isDownloaded: boolean = false;

  zoomedImageUrl: string | null = null;

  applyPreprocessing: boolean = true; 

  showMappingModal = false;
  fileLabelInfo: FileLabelInfo | null = null;
  labelMapping: Record<string, string> = {};
  isFetchingLabels = false;

  constructor(
    public workflowService: WorkflowService,
    private aiModelsService: AiModelsService,
    private tutorialService: TutorialService
  ) {}

  ngOnInit(): void {
    this.tutorialService.showAiTutorial$.subscribe(show => {
    console.log('AI tutorial state:', show);
    this.showAiTutorial = show;
  });

    const file = this.workflowService.getUploadedFile();
    this.uploadedFileName = file ? file.name : 'No file selected';
    this.fetchFileLabels();
    this.fetchAvailableModels();
  }

  onAiTutorialClosed(): void {
    this.tutorialService.markAiTutorialSeen();
  }

  showAiTutorialAgain(): void {
    this.tutorialService.resetAiTutorial();
  }

  onGhostBarActive(active: boolean): void {
    this.tutorialGhostBarActive = active;
  }

  expandedDescriptions = new Set<string>();

  toggleDescription(modelId: string, event: Event): void {
    event.stopPropagation();
    if (this.expandedDescriptions.has(modelId)) {
      this.expandedDescriptions.delete(modelId);
    } else {
      this.expandedDescriptions.add(modelId);
    }
  }

  isDescriptionExpanded(modelId: string): boolean {
    return this.expandedDescriptions.has(modelId);
  }

  getImageUrl(url?: string): string {
    return this.aiModelsService.getImageUrl(url);
  }

  fetchAvailableModels(): void {
    this.aiModelsService.getAvailableModels().subscribe({
      next: (data) => {
        this.models = data;
      },
      error: (err) => {
        console.error('Failed to load models:', err);
        this.errorMessage = 'Could not load AI models from the server.';
      }
    });
  }

  fetchFileLabels(): void {
    const configId = this.workflowService.getConfiguredFileId();
    if (!configId) return;

    this.isFetchingLabels = true;
    this.aiModelsService.getFileLabels(configId).subscribe({
      next: (info) => {
        this.fileLabelInfo = info;
        this.isFetchingLabels = false;
      },
      error: () => {
        this.isFetchingLabels = false;
      },
    });
  }

  selectModel(id: string): void {
    this.selectedModelId = id;
    this.errorMessage = '';
    this.labelMapping = {};
  }

  getSelectedModel() {
    return this.models.find(m => m.id === this.selectedModelId);
  }
  
  getSelectedModelName(): string {
    const model = this.models.find(m => m.id === this.selectedModelId);
    return model ? model.name : '';
  }

  get canMapLabels(): boolean {
    return !!this.selectedModelId;
  }

  getLabelDisplayName(labelNum: number): string {
    if (!this.fileLabelInfo) return `Label ${labelNum}`;
    const entry = Object.entries(this.fileLabelInfo.detailed_labels).find(
      ([, num]) => num === labelNum
    );
    return entry ? `${labelNum}  —  "${entry[0]}"` : `Label ${labelNum}`;
  }

  get isMappingComplete(): boolean {
    if (!this.fileLabelInfo || this.fileLabelInfo.labels.length === 0) return true;
    return this.fileLabelInfo.labels.every(
      (lbl) => !!this.labelMapping[String(lbl)]
    );
  }

  openMappingModal(): void {
    if (!this.hasFileLabels) return;
    this.showMappingModal = true;
  }

  get hasFileLabels(): boolean {
    return (this.fileLabelInfo?.labels?.length ?? 0) > 0;
  }

  closeMappingModal(): void {
    this.showMappingModal = false;
  }

  confirmMapping(): void {
    this.showMappingModal = false;
  }

  clearMapping(): void {
    this.labelMapping = {};
  }

  runInference(): void {
    if (!this.selectedModelId) return;

    const configId = this.workflowService.getConfiguredFileId();
    if (!configId) {
      this.errorMessage = 'No valid data configuration found. Please upload or preprocess a file first.';
      return;
    }

    this.isProcessing = true;
    this.errorMessage = '';
    this.predictionResults = null;
    this.inferenceSummary = null;
    this.isDownloaded = false;

    const mappingToSend =
      this.fileLabelInfo && this.fileLabelInfo.labels.length > 0 && this.isMappingComplete
        ? this.labelMapping
        : undefined;

    // 👈 4. PASS THE TOGGLE STATE IN THE PAYLOAD
    this.aiModelsService.runInference({ 
      model_id: this.selectedModelId, 
      config_id: configId,
      apply_preprocessing: this.applyPreprocessing,
      label_mapping: mappingToSend,
    }).subscribe({
      next: (response) => {
        this.isProcessing = false;
        this.predictionResults = response.predictions;
        this.inferenceSummary = response.summary;
        this.currentResultId = response.result_id || null;
      },
      error: (err) => {
        this.isProcessing = false;
        this.errorMessage = err.error?.detail || 'AI Inference failed. Please check the data format.';
        console.error('Inference error:', err);
      }
    });
  }
  openImageOverlay(model: any, event: Event): void {
    event.stopPropagation();
    event.preventDefault();

    console.log('Model data:', model); // Debug: See what's in the model

    // Try multiple possible locations for the image
    let imagePath = null;

    if (model.files?.image) {
      imagePath = model.files.image;
      console.log('Found image in files.image:', imagePath);
    } else if (model.image_url) {
      imagePath = model.image_url;
      console.log('Found image in image_url:', imagePath);
    }

    if (imagePath) {
      const fullUrl = this.getImageUrl(imagePath);
      console.log('Full URL being opened:', fullUrl);
      this.zoomedImageUrl = fullUrl;
    } else {
      console.error('No image found for model:', model);
      this.errorMessage = 'No architecture image available for this model.';
      setTimeout(() => this.errorMessage = '', 3000);
    }
  }

  closeImageOverlay(): void {
    this.zoomedImageUrl = null;
  }

  downloadCSV(): void {
    if (!this.currentResultId) {
      this.errorMessage = 'No results available to download.';
      return;
    }

    this.aiModelsService.downloadCSV(this.currentResultId).subscribe({
      next: (blob: Blob) => {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        
        // Generate dynamic filename matching the user's request
        const modelName = this.getSelectedModelName().replace(/\s+/g, '_');
        const timestamp = new Date().toISOString().replace(/T/, '_').replace(/:/g, '').split('.')[0];
        a.download = `predictions_${modelName}_${timestamp}.csv`;
        
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);

        // Change button state to "Saved!" for 3 seconds
        this.isDownloaded = true;
        setTimeout(() => {
          this.isDownloaded = false;
        }, 3000);
      },
      error: (err) => {
        console.error('Failed to download CSV:', err);
        this.errorMessage = 'Failed to download CSV file. It might have expired.';
      }
    });
  }

  resetView(): void {
    this.predictionResults = null;
    this.inferenceSummary = null;
    this.currentResultId = null;
    this.isDownloaded = false;
    this.errorMessage = '';
  }

  objectKeys(obj: any): string[] {
    return Object.keys(obj || {});
  }

  get hasGroundTruth(): boolean {
    return !!this.predictionResults?.[0]?.trueClass;
  }
}