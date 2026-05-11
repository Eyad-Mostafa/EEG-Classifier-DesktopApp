import { Component, OnInit, ViewChild } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterModule } from '@angular/router';
import { FormsModule } from '@angular/forms';
import {
  CdkDragDrop,
  moveItemInArray,
  DragDropModule,
} from '@angular/cdk/drag-drop';
import { ScrollingModule, CdkScrollable } from '@angular/cdk/scrolling';

import { firstValueFrom } from 'rxjs';
import { WorkflowService } from '../../services/workflow.service';
import { AlgorithmService } from '../../services/algorithm.service';
import { PreprocessingService } from '../../services/preprocessing.service';
import { TutorialService } from '../../services/tutorial.service';
import { PipelineService } from '../../services/pipeline.service';

import { TutorialOverlayComponent } from '../ui/tutorial-overlay/tutorial-overlay.component';
import { AlgorithmDetailsComponent } from '../algorithm-details/algorithm-details.component';
import { SavePipelineModalComponent } from '../save-pipeline-modal/save-pipeline-modal.component';
import { PipelinePanelComponent } from '../preprocessing-config/pipeline-panel/pipeline-panel.component';

import { AlgorithmUI, ParameterUI } from '../../models/ui/forms.ui';
import { AlgorithmInfo } from '../../models/api/algorithm-library.model.api';
import { DomainType } from '../../models/api/preprocessing.model.api';
import { PreprocessingError } from '../../models/ui/errors.ui';
import { SavedPipeline } from '../../models/pipeline.model';
import { AppLoaderComponent } from '../ui/app-loader/app-loader.component';

import { ValidatorsUtil } from '../../utils/validators';
import { PipelineMapper } from '../../utils/pipeline.mapper';

@Component({
  selector: 'app-preprocessing-config',
  standalone: true,
  imports: [
    CommonModule,
    ScrollingModule,
    DragDropModule,
    FormsModule,
    TutorialOverlayComponent,
    RouterModule,
    AlgorithmDetailsComponent,
    AppLoaderComponent,
    SavePipelineModalComponent,
    PipelinePanelComponent,
  ],
  templateUrl: './preprocessing-config.component.html',
  styleUrls: ['./preprocessing-config.component.css'],
})
export class PreprocessingConfigComponent implements OnInit {
  @ViewChild(CdkScrollable) private cdkScrollable?: CdkScrollable;

  algorithms: AlgorithmUI[] = [];
  expandedAlgorithm: string | null = null;
  selectedDomain: DomainType = DomainType.TIME;
  selectedAlgorithmDetails: AlgorithmUI | null = null;

  showDetailsPanel = false;
  isLoading = false;
  errorMessage: string = '';
  serverError: PreprocessingError | null = null;
  showParameterErrors = false;
  showTutorial = false;
  showSavePipelineModal = false;
  showPipelinePanel = false;
  isErrorExpanded: boolean = false;

  currentFileName: string | null = null;

  // Store the uploaded file ID at the beginning
  private uploadedFileId: string | null = null;
  private isAutoSaving = false;
  private configId: string | null = null;


  constructor(
    public workflowService: WorkflowService,
    private router: Router,
    private algorithmService: AlgorithmService,
    private preprocessingService: PreprocessingService,
    private tutorialService: TutorialService,
    private pipelineService: PipelineService
  ) { }

  ngOnInit(): void {
    // Store the uploaded file ID once at the start
    this.configId = this.workflowService.getConfiguredFileId();
    this.currentFileName = this.workflowService.getUploadedFileName();

    this.tutorialService.showTutorial$.subscribe(
      (show) => (this.showTutorial = show)
    );

    if (!this.configId) {
      this.router.navigate(['/upload']);
      return;
    }

    const savedState = this.workflowService.getPreprocessingUIState();

    if (savedState) {
      this.algorithms = savedState.algorithms;
      this.selectedDomain = savedState.selectedDomain;
    } else {
      this.loadAlgorithms();
    }
    this.handleNavbar();
  }

  private setError(message: string): void {
    this.errorMessage = message;

    setTimeout(() => {
      const el = this.cdkScrollable?.getElementRef()?.nativeElement as
        | HTMLElement
        | undefined;

      if (el && typeof (el as any).scrollTo === 'function') {
        (el as any).scrollTo({ top: 0, behavior: 'smooth' });
      } else {
        window.scrollTo({ top: 0, behavior: 'smooth' });
      }
    }, 0);
  }

  private clearError(): void {
    this.errorMessage = '';
  }

  private loadAlgorithms(): void {
    this.clearError();
    this.isLoading = true;
    this.serverError = null;

    this.algorithmService.getAllAlgorithms().subscribe({
      next: (data: AlgorithmInfo[]) => {
        if (!data || data.length === 0) {
          this.setError('No algorithms available.');
          this.isLoading = false;
          return;
        }

        this.algorithms = data
          .filter((info) => {
            const isAnalysis =
              info.type === 'analysis' || (info as any).method_id !== undefined;
            return !isAnalysis;
          })
          .map(
            (info) =>
            ({
              ...info,
              enabled: true,
              isExpanded: false,
              params: info.parameters.map((p) => ({
                ...p,
                value: p.value ?? p.default ?? '',
                hasError: false,
                errorMessage: '',
              })),
            } as AlgorithmUI)
          );

        this.pipelineService.setAlgorithms(data);
        this.isLoading = false;
      },
      error: (err) => {
        console.error('❌ Error fetching algorithms:', err);
        this.setError(
          'Failed to load algorithms. Please check if the server is online.'
        );
        this.isLoading = false;
      },
    });
  }

  async handleStartPreprocessing(): Promise<void> {
    const configuredFileId = this.workflowService.getConfiguredFileId();
    if (!configuredFileId) {
      this.setError('No file selected. Please upload a file first.');
      return;
    }

    this.clearError();
    this.serverError = null;

    if (this.validateForm()) {
      return;
    }

    this.isLoading = true;

    const pipelinePayload = PipelineMapper.toApiPipeline(
      this.algorithms,
      this.selectedDomain
    );
    const resultsConfig = PipelineMapper.toResultsConfig(
      this.algorithms,
      this.selectedDomain
    );

    // AUTO-SAVE - uses stored configId
    const existingPipelineId = this.workflowService.getPipelineId();
    if (!this.isAutoSaving && this.configId && !existingPipelineId) {
      this.isAutoSaving = true;
      try {
        const enabledCount = this.algorithms.filter(a => a.enabled && a.domainType === this.selectedDomain).length;
        if (enabledCount > 0) {
          console.log(`Auto-saving pipeline with ${enabledCount} algorithms...`);
          const autoName = `${this.currentFileName || 'pipeline'} - ${new Date().toLocaleString()}`;

          const savedPipeline = await this.pipelineService.savePipeline(
            autoName,
            'file-specific',
            { algorithms: this.algorithms, selectedDomain: this.selectedDomain },
            this.configId,
            this.currentFileName || 'unknown',
            `Auto-saved on ${new Date().toLocaleString()}`
          );
          this.workflowService.setPipelineId(Number(savedPipeline.id));
          console.log('Pipeline auto-saved successfully');
        }
      } catch (error) {
        console.warn('Auto-save failed, continuing with preprocessing:', error);
      } finally {
        setTimeout(() => {
          this.isAutoSaving = false;
        }, 2000);
      }
    } else if (!this.configId) {
      console.warn('Cannot auto-save: No config ID available');
    } else if (existingPipelineId) {
      console.log('Using existing loaded pipeline, skipping auto-save');
    } else {
      console.log('Auto-save already in progress, skipping');
    }

    setTimeout(() => {
      const startTime = performance.now();

      this.preprocessingService
        .runPreprocessing(
          configuredFileId,
          this.workflowService.getSamplingRate()!,
          pipelinePayload
        )
        .subscribe({
          next: (response) => {
            const endTime = performance.now();
            const totalTimeSec = ((endTime - startTime) / 1000).toFixed(2);

            this.workflowService.setPreprocessingResult(response);
            this.workflowService.setPreprocessingConfig(resultsConfig);

            this.workflowService.setResultFileId(response.result_id);
            this.workflowService.setResultFileName(response.file_name);
            this.workflowService.setSamplingRate(response.sampling_rate);
            this.workflowService.setResultFileSize(
              response.file_size_mb + ' MB'
            );
            this.workflowService.setProcessingTime(totalTimeSec);

            if (response.figure_data_original) {
              this.workflowService.setFigureOriginalData(
                response.figure_data_original
              );
            }
            if (response.figure_data_processed) {
              this.workflowService.setFigureProcessedData(
                response.figure_data_processed
              );
            }

            this.workflowService.setDomainType(response.domainType);

            this.workflowService.setNavState({
              '/results': false,
            });
            this.isLoading = false;
            this.router.navigate(['/results']);
          },
          error: (err) => {
            console.error('Processing error:', err);
            this.isLoading = false;

            const msg =
              err?.error?.detail ||
              err?.message ||
              'Preprocessing failed due to a server error.';

            this.setError(msg);
            this.serverError = err;
          },
        });
    }, 50);
  }

  async onLoadPipeline(pipeline: SavedPipeline): Promise<void> {
    console.log('===== LOADING PIPELINE =====', pipeline);

    try {
      if (pipeline.config && pipeline.config.algorithms) {
        this.workflowService.setPipelineId(Number(pipeline.id));
        const savedDomain = pipeline.config.selectedDomain;

        const updatedAlgorithms = this.algorithms.map(savedAlgo => {
          const loadedAlgo = pipeline.config.algorithms.find(
            (la: any) => la.id === savedAlgo.id
          );

          if (loadedAlgo && loadedAlgo.enabled) {
            const updatedParams = savedAlgo.params.map(param => {
              const savedParam = loadedAlgo.params.find((p: any) => p.name === param.name);
              if (savedParam && savedParam.value !== undefined && savedParam.value !== '') {
                return { ...param, value: savedParam.value };
              }
              return param;
            });

            return {
              ...savedAlgo,
              enabled: true,
              params: updatedParams,
              domainType: loadedAlgo.domainType || savedDomain
            };
          }
          return { ...savedAlgo, enabled: false };
        });

        this.algorithms = updatedAlgorithms;
        this.selectedDomain = savedDomain || DomainType.TIME;
        this.algorithms = this.sortAlgorithmsByEnabled();

        this.showPipelinePanel = false;
        this.saveState();

        console.log(`Pipeline loaded with ${this.selectedDomain} domain`);
      } else {
        console.error('Pipeline has no algorithms to load');
      }
    } catch (error) {
      console.error('Failed to load pipeline:', error);
    }
  }

  private sortAlgorithmsByEnabled(): AlgorithmUI[] {
    const enabled = this.algorithms.filter(a => a.enabled);
    const disabled = this.algorithms.filter(a => !a.enabled);
    return [...enabled, ...disabled];
  }

  private validateForm(): boolean {
    this.showParameterErrors = true;
    let hasError = false;
    let firstErrorId: string | null = null;

    this.algorithms.forEach((algo) => {
      if (algo.enabled && this.isAlgorithmInSelectedDomain(algo)) {
        algo.params.forEach((p) => {
          if (!ValidatorsUtil.validateParameter(p, true)) {
            hasError = true;
            if (!firstErrorId) firstErrorId = algo.id;
          }
        });
      }
    });

    if (hasError && firstErrorId) {
      this.expandedAlgorithm = firstErrorId;
      this.scrollToError('.has-error');
    }

    return hasError;
  }

  toggleAlgorithm(id: string): void {
    const algo = this.algorithms.find((a) => a.id === id);
    if (algo) algo.enabled = !algo.enabled;
    this.workflowService.setPipelineId(null);
    this.saveState();
  }

  toggleExpanded(id: string): void {
    this.expandedAlgorithm = this.expandedAlgorithm === id ? null : id;
  }

  switchDomain(domain: string): void {
    this.selectedDomain = domain as DomainType;
    this.expandedAlgorithm = null;
    this.showParameterErrors = false;
    this.serverError = null;
    this.clearError();

    this.algorithms.forEach((algo) => {
      algo.params.forEach((p) => {
        p.hasError = false;
        p.errorMessage = '';
      });
    });
    this.workflowService.setPipelineId(null);
    this.saveState();
  }

  retryPreprocessing(): void {
    this.showParameterErrors = false;
    this.serverError = null;
    this.clearError();
    this.handleStartPreprocessing();
  }

  drop(event: CdkDragDrop<AlgorithmUI[]>): void {
    const filtered = this.filteredAlgorithms;
    moveItemInArray(filtered, event.previousIndex, event.currentIndex);

    const enabled = filtered.filter((a) => a.enabled);
    const disabled = filtered.filter((a) => !a.enabled);
    const others = this.algorithms.filter(
      (a) => !this.isAlgorithmInSelectedDomain(a)
    );

    this.algorithms = [...enabled, ...disabled, ...others];
    this.workflowService.setPipelineId(null);
    this.saveState();
  }

  get filteredAlgorithms(): AlgorithmUI[] {
    return this.algorithms.filter((a) => this.isAlgorithmInSelectedDomain(a));
  }

  get sortedAlgorithms(): AlgorithmUI[] {
    return this.filteredAlgorithms.sort(
      (a, b) => Number(b.enabled) - Number(a.enabled)
    );
  }

  private isAlgorithmInSelectedDomain(a: AlgorithmUI): boolean {
    return a.domainType === this.selectedDomain;
  }

  get DomainType() {
    return DomainType;
  }

  hasNextEnabled(list: AlgorithmUI[], index: number): boolean {
    return list.slice(index + 1).some((a) => a.enabled);
  }

  get hasEnabledAlgorithms(): boolean {
    return this.filteredAlgorithms.some((a) => a.enabled);
  }

  get invalidParametersCount(): number {
    let count = 0;
    this.algorithms.forEach((algo) => {
      if (algo.enabled && algo.params)
        count += algo.params.filter((p) => p.hasError).length;
    });
    return count;
  }

  get hasInvalidParameters(): boolean {
    return this.algorithms.some(
      (algo) => algo.enabled && algo.params.some((p) => p.hasError)
    );
  }

  getAlgorithmHasErrors(algorithm: AlgorithmUI): boolean {
    if (!algorithm.enabled || !algorithm.params) return false;
    return algorithm.params.some((p) => p.hasError);
  }

  getErrorCount(algorithm: AlgorithmUI): number {
    if (!algorithm.enabled || !algorithm.params) return 0;
    return algorithm.params.filter((p) => p.hasError).length;
  }

  onParameterChange(param: ParameterUI): void {
    ValidatorsUtil.validateParameter(param, this.showParameterErrors);
    this.workflowService.setPipelineId(null);
    this.saveState();
  }

  getParameterPlaceholder(param: ParameterUI): string {
    if (param.default !== undefined && param.default !== '')
      return `Default: ${param.default}`;
    return param.required ? 'Required' : 'Enter value';
  }

  getRequiredTooltip(param: ParameterUI): string {
    return param.required ? 'Required Field' : 'Optional';
  }

  getParameterConstraints(param: ParameterUI): string {
    const constraints = [];
    if (param.min !== undefined) constraints.push(`min: ${param.min}`);
    if (param.max !== undefined) constraints.push(`max: ${param.max}`);
    if (param.options?.length)
      constraints.push(`options: ${param.options.join(', ')}`);
    return constraints.join(' • ');
  }

  isParameterValid(param: ParameterUI): boolean {
    return param.value !== undefined && param.value !== '' && !param.hasError;
  }

  getParameterUnit(param: ParameterUI): string {
    const match = param.name.match(/\((.*?)\)/);
    return match ? match[1] : '';
  }

  handleBack(): void {
    this.router.navigate(['/config']);
  }

  showAgain(): void {
    this.tutorialService.resetTutorial();
  }

  onTutorialClosed(): void {
    this.tutorialService.markAsSeen();
  }

  private scrollToError(selector: string): void {
    setTimeout(() => {
      const el = document.querySelector(selector);
      if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }, 100);
  }

  trackByAlgorithmId(index: number, item: any): string {
    return item.id;
  }

  openDetails(algorithm: AlgorithmUI): void {
    this.selectedAlgorithmDetails = algorithm;
    this.showDetailsPanel = true;
    document.body.style.overflow = 'hidden';
  }

  closeDetails(): void {
    this.showDetailsPanel = false;
    setTimeout(() => {
      this.selectedAlgorithmDetails = null;
    }, 300);
  }

  handleNavbar(): void {
    this.workflowService.setNavState({
      '/upload': false,
      '/preprocess': false,
      '/analysis': false,
      '/visualization': false,
      '/algorithms': false,
    });
  }

  private saveState(): void {
    this.workflowService.setPreprocessingUIState({
      algorithms: this.algorithms,
      selectedDomain: this.selectedDomain,
    });
  }

  openSavePipelineModal(): void {
    this.showSavePipelineModal = true;
  }

  openPipelinePanel(): void {
    const fileId = this.workflowService.getUploadedFileId();
    if (!fileId) {
      console.warn('No file ID available for pipeline panel');
      alert('Please upload a file first to see file-specific pipelines');
    }
    this.showPipelinePanel = true;
  }

  async onSavePipeline(event: { name: string; type: 'global' | 'file-specific'; notes: string }): Promise<void> {
    const fileId = this.workflowService.getUploadedFileId();
    const fileName = this.workflowService.getUploadedFileName();

    console.log('🔍 SAVING PIPELINE DEBUG:');
    console.log('  Event Type:', event.type);
    console.log('  Uploaded File ID:', fileId);
    console.log('  File Name:', fileName);
    console.log('  Pipeline Name:', event.name);

    if (event.type === 'file-specific' && !fileId) {
      console.error('Cannot save file-specific pipeline: No file ID available');
      alert('Cannot save file-specific pipeline: No file loaded');
      return;
    }

    // ✅ CLOSE MODAL IMMEDIATELY to prevent double clicks
    this.showSavePipelineModal = false;

    try {
      const savedPipeline = await this.pipelineService.savePipeline(
        event.name,
        event.type,
        {
          algorithms: this.algorithms,
          selectedDomain: this.selectedDomain
        },
        event.type === 'file-specific' ? this.configId || undefined : undefined,
        event.type === 'file-specific' ? fileName || undefined : undefined,
        event.notes
      );

      if (event.type === 'file-specific') {
        this.workflowService.setPipelineId(Number(savedPipeline.id));
      }

      console.log('Pipeline saved successfully');

      // Refresh pipeline panel if open
      if (this.showPipelinePanel) {
        this.showPipelinePanel = false;
        setTimeout(() => {
          this.showPipelinePanel = true;
        }, 100);
      }

    } catch (error) {
      console.error('Failed to save pipeline:', error);
      alert('Failed to save pipeline. Check console for details.');
    }
  }
}