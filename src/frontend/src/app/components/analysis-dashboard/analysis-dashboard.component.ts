import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { FormsModule } from '@angular/forms';

import { AnalysisService } from '../../services/analysis.service';
import { WorkflowService } from '../../services/workflow.service';
import { AlgorithmDetailsComponent } from '../algorithm-details/algorithm-details.component';

import {
  AnalysisResponse,
  AnalysisModule,
  AnalysisResult,
} from '../../models/api/analysis.api';
import { AppLoaderComponent } from '../ui/app-loader/app-loader.component';
import { DomainType } from '../../models/api/preprocessing.model.api';

@Component({
  selector: 'app-analysis-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    AlgorithmDetailsComponent,
    AppLoaderComponent,
  ],
  templateUrl: './analysis-dashboard.component.html',
  styleUrls: [],
})
export class AnalysisDashboardComponent implements OnInit {

  // 1. Store ALL methods from API here
  allAnalysisMethods: AnalysisModule[] = [];
  // 2. Store FILTERED methods here (Use this in your HTML *ngFor)
  displayedMethods: AnalysisModule[] = [];

  // Keep this for compatibility if your HTML still references it, 
  // but ideally point your HTML to displayedMethods
  analysisMethods: AnalysisModule[] = [];

  activeTab: 'overview' | 'detailed' = 'overview';
  expandedModuleId: string | null = null;
  private runningMethods: Set<string> = new Set();  errorMessage: string = '';
  expandedPreviews: { [key: string]: boolean } = {};

  private isRunningAnalysis = false;
  private analysisQueue: string[] = [];
  // Expose Enum to Template
  DomainType = DomainType;

  selectedFileType: 'uploaded' | 'result' = 'uploaded';
  selectedAlgorithmId: string | null = null;
  showDetailsPanel = false;

  constructor(
    private analysisService: AnalysisService,
    public workflowService: WorkflowService,
    private router: Router
  ) { }

  ngOnInit(): void {
    // Auto-select result file if available
    if (this.workflowService.getResultFileId()) {
      this.selectedFileType = 'result';
    }

    this.loadAnalysisMethods();
    this.handleNavbar();
  }

  loadAnalysisMethods(): void {
    this.analysisService.getAllAnalysisMethods().subscribe({
      next: (methods) => {
        // 1. SAVE THE MASTER LIST (Critical Step)
        this.allAnalysisMethods = methods;

        // 2. Initialize the display list (fallback)
        this.analysisMethods = methods;
        this.displayedMethods = methods;

        // 3. Apply the initial filter based on the current file
        this.filterMethodsByDomain();
        this.restoreCachedAnalysisResults();
      },
      error: (error) => {
        console.error('Failed to load analysis methods:', error);
        this.errorMessage = 'Failed to load available analysis methods.';
      },
    });
  }

  filterMethodsByDomain(): void {
    // Safety check: Don't run if we haven't loaded data yet
    if (!this.allAnalysisMethods || this.allAnalysisMethods.length === 0) {
      return;
    }

    let currentDomain: DomainType;

    // 1. Determine the target domain
    if (this.selectedFileType === 'uploaded') {
      currentDomain = DomainType.TIME; // Original files are always Time
    } else {
      // Processed files: use stored domain, default to Time if missing
      currentDomain = this.workflowService.getDomainType() || DomainType.TIME;
    }

    // 2. Filter from the MASTER LIST (allAnalysisMethods)
    // We check if the method's allowed list includes the current domain
    this.displayedMethods = this.allAnalysisMethods.filter(method =>
      method.allowedDomainTypes && method.allowedDomainTypes.includes(currentDomain)
    );

    // 3. Update legacy property (if your HTML uses it)
    this.analysisMethods = this.displayedMethods;

    console.log(`[Filter] Selected: ${this.selectedFileType}, Domain: ${currentDomain}. Showing ${this.displayedMethods.length} / ${this.allAnalysisMethods.length} methods.`);
  }

  // TRIGGER: Call filter whenever the user switches the file radio button
  onFileTypeChange(): void {
    this.filterMethodsByDomain();
    this.restoreCachedAnalysisResults();
    // Clear expanded details to avoid UI confusion
    this.expandedModuleId = null;
  }

  setActiveTab(tab: 'overview' | 'detailed'): void {
    this.activeTab = tab;
  }

  toggleMethodExpansion(methodId: string): void {
    this.expandedModuleId =
      this.expandedModuleId === methodId ? null : methodId;
  }

  runAnalysis(methodId: string): void {
    const runningKey = `${methodId}_${this.selectedFileType}`;
    this.runningMethods.add(runningKey);
    // Add to queue if already running
    if (this.isRunningAnalysis) {
      this.analysisQueue.push(methodId);
      console.log(`Added ${methodId} to queue. Queue length: ${this.analysisQueue.length}`);
      return;
    }

    this.executeAnalysis(methodId);
  }

  private getAnalysisSourceType(): 'configured' | 'preprocessed' {
    return this.selectedFileType === 'uploaded' ? 'configured' : 'preprocessed';
  }

  private getAnalysisPipelineId(): number | null {
    return this.selectedFileType === 'uploaded'
      ? null
      : this.workflowService.getPipelineId();
  }

  executeAnalysis(methodId: string): void {
    this.isRunningAnalysis = true;
    const runningKey = `${methodId}_${this.selectedFileType}`;
    //this.runningMethods.add(runningKey);
    this.errorMessage = '';

    const fileId = this.selectedFileType === 'uploaded'
      ? this.workflowService.getConfiguredFileId()
      : this.workflowService.getResultFileId();

    const configId = this.workflowService.getConfiguredFileId();
    const sourceType = this.getAnalysisSourceType();
    const pipelineId = this.getAnalysisPipelineId();

    if (!fileId) {
      this.errorMessage = 'No valid file selected. Please upload or preprocess data first.';
      this.runningMethods.delete(runningKey);
      this.isRunningAnalysis = false;
      this.processNextInQueue();
      return;
    }

    if (!configId) {
      this.errorMessage = 'No configuration found. Please configure the file first.';
      this.runningMethods.delete(runningKey);
      this.isRunningAnalysis = false;
      this.processNextInQueue();
      return;
    }

    this.analysisService
      .runAnalysis(
        methodId,
        fileId,
        configId,
        pipelineId,
        sourceType,
        this.workflowService.getSamplingRate()!,
        {}
      )
      .subscribe({
        next: (response: AnalysisResponse) => {
          if (response.success) {
            this.workflowService.setAnalysisResult(
              methodId,
              this.selectedFileType,
              fileId,
              response.result
            );
          } else {
            this.errorMessage = 'Analysis ran but returned failure status.';
          }
          this.runningMethods.delete(runningKey);
          this.isRunningAnalysis = false;
          this.processNextInQueue();
        },
        error: (error) => {
          console.error('Analysis failed:', error);
          this.errorMessage = error.error?.detail || error.message || 'Analysis failed';
          this.runningMethods.delete(runningKey);
          this.isRunningAnalysis = false;
          this.processNextInQueue();
        },
      });
  }

  private processNextInQueue(): void {
    if (this.analysisQueue.length > 0) {
      const nextMethodId = this.analysisQueue.shift();
      if (nextMethodId) {
        this.executeAnalysis(nextMethodId);
      }
    }
  }
 
  isMethodPending(methodId: string): boolean {
    const key = `${methodId}_${this.selectedFileType}`;
    return this.runningMethods.has(key);
  }

  // --- Template Helpers ---

  hasAnalysisResults(methodId: string): boolean {
    const fileId =
      this.selectedFileType === 'uploaded'
        ? this.workflowService.getConfiguredFileId()
        : this.workflowService.getResultFileId();
    if (!fileId) return false;
    return this.workflowService.hasAnalysisResult(methodId, this.selectedFileType, fileId);
  }

  getAnalysisResults(methodId: string): AnalysisResult | null {
    const fileId =
      this.selectedFileType === 'uploaded'
        ? this.workflowService.getConfiguredFileId()
        : this.workflowService.getResultFileId();
    if (!fileId) return null;
    return this.workflowService.getAnalysisResult(methodId, this.selectedFileType, fileId) || null;
  }

  getTopographicMapData(methodId: string): string | null {
    const resultObj = this.getAnalysisResults(methodId);

    if (
      resultObj?.visualization_data &&
      resultObj.visualization_data['topographic_map']
    ) {
      const base64 = resultObj.visualization_data['topographic_map'];
      return base64.startsWith('data:image')
        ? base64
        : `data:image/png;base64,${base64}`;
    }
    return null;
  }

  isArray(val: any): boolean {
    return Array.isArray(val);
  }

  isObject(val: any): boolean {
    return typeof val === 'object' && val !== null && !Array.isArray(val);
  }

  isPrimitive(val: any): boolean {
    return (
      typeof val === 'string' ||
      typeof val === 'number' ||
      typeof val === 'boolean'
    );
  }

  getAsArray(val: any): any[] {
    return val as any[];
  }

  getAsObject(val: any): Record<string, any> {
    return val as Record<string, any>;
  }

  formatKey(key: string): string {
    // Converts "mean_entropy" -> "Mean Entropy"
    return key.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());
  }

  copyData(data: any): void {
    if (!data) return;
    const jsonString = JSON.stringify(data, null, 2);
    navigator.clipboard.writeText(jsonString).then(() => {
      console.log('Copied to clipboard');
    });
  }

  // --- Navigation & Drawer ---

  openDetails(method: AnalysisModule): void {
    this.selectedAlgorithmId = method.id;
    this.showDetailsPanel = true;
    document.body.style.overflow = 'hidden';
  }

  closeDetails(): void {
    this.showDetailsPanel = false;
    document.body.style.overflow = '';
    setTimeout(() => (this.selectedAlgorithmId = null), 300);
  }

  navigateToVisualization(): void {
    this.router.navigate(['/visualization']);
  }
  navigateToPreprocessing(): void {
    this.router.navigate(['/preprocess']);
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

  private restoreCachedAnalysisResults(): void {
    const configId = this.workflowService.getConfiguredFileId();
    const sourceType = this.getAnalysisSourceType();
    const pipelineId = this.getAnalysisPipelineId();
    const fileId =
      this.selectedFileType === 'uploaded'
        ? this.workflowService.getConfiguredFileId()
        : this.workflowService.getResultFileId();

    if (!configId || !fileId) {
      return;
    }

    this.analysisService.getAnalysisHistory(configId, pipelineId, sourceType).subscribe({
      next: (response) => {
        if (!response?.items?.length) {
          return;
        }

        for (const item of response.items) {
          this.workflowService.setAnalysisResult(
            item.method_id,
            this.selectedFileType,
            fileId,
            item.result
          );
        }
      },
      error: (error) => {
        console.error('Failed to restore cached analysis results:', error);
      },
    });
  }

}