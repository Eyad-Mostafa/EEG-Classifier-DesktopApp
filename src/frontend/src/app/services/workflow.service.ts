import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';
import { AlgorithmStep, DomainType } from '../models/api/preprocessing.model.api';
import { AnalysisResult } from '../models/api/analysis.api';
import { EEGSubjectData } from '../models/api/visualisation';

@Injectable({
  providedIn: 'root',
})
export class WorkflowService {
  private uploadedFileSubject = new BehaviorSubject<File | null>(null);
  private uploadedFileIdSubject = new BehaviorSubject<string | null>(null);
  private configuredFileIdSubject = new BehaviorSubject<string | null>(null);
  private samplingRateSubject = new BehaviorSubject<number>(0);
  private uploadedFileNameSubject = new BehaviorSubject<string | null>(null);
  private resultFileIdSubject = new BehaviorSubject<string | null>(null);
  private preprocessingConfigSubject = new BehaviorSubject<
    AlgorithmStep[] | null
  >(null);
  private preprocessingResult: any = null;
  private resultFileNameSubject = new BehaviorSubject<string | null>(null);
  private navStateSource = new BehaviorSubject<{ [key: string]: boolean }>({});
  private analysisCache = new Map<string, AnalysisResult>();
  private domainTypeSubject = new BehaviorSubject<DomainType | null>(null);
  private configIdSubject = new BehaviorSubject<string | null>(null);
  private pipelineIdSubject = new BehaviorSubject<number | null>(null);

  private fileConfigUIState: {
    labelValues: Record<string, string>;
    channelMapping: Record<string, string>;
    selectionState: Record<string, Record<string, Record<string, boolean>>>;
    selectedMontage: string;
    selectedLabels?: Record<string, boolean>; 
    selectedChannels?: Record<string, boolean>
    restoreModalSeen: boolean;
  } | null = null;

  setFileConfigUIState(state: {
    labelValues: Record<string, string>;
    channelMapping: Record<string, string>;
    selectionState: Record<string, Record<string, Record<string, boolean>>>;
    selectedMontage: string;
    selectedLabels?: Record<string, boolean>;
    selectedChannels?: Record<string, boolean>;
    restoreModalSeen: boolean;
  }) {
    this.fileConfigUIState = state;
  }

  getFileConfigUIState() {
    return this.fileConfigUIState;
  }

  private preprocessingUIState: {
    algorithms: any[];
    selectedDomain: DomainType;
  } | null = null;

  setPreprocessingUIState(state: {
    algorithms: any[];
    selectedDomain: DomainType;
  }) {
    this.preprocessingUIState = state;
  }

  getPreprocessingUIState() {
    return this.preprocessingUIState;
  }

  private visualizationState: {
    rawSubjects?: EEGSubjectData[];
    cleanSubjects?: EEGSubjectData[];
    dynamicPlots?: any[];
    rawData?: any;
    cleanData?: any;
    spectrogramRaw?: any[];
    spectrogramClean?: any[];
  } | null = null;

  uploadedFile$ = this.uploadedFileSubject.asObservable();
  uploadedFileId$ = this.uploadedFileIdSubject.asObservable();
  configuredFileId$ = this.configuredFileIdSubject.asObservable();
  resultFileId$ = this.resultFileIdSubject.asObservable();
  uploadedFileName$ = this.uploadedFileNameSubject.asObservable();
  preprocessingConfig$ = this.preprocessingConfigSubject.asObservable();
  navState$ = this.navStateSource.asObservable();
  resultFileName$ = this.resultFileNameSubject.asObservable();
  domainType$ = this.domainTypeSubject.asObservable();
  pipelineId$ = this.pipelineIdSubject.asObservable();

  constructor() { }

  setPipelineId(pipelineId: number | null): void {
    this.pipelineIdSubject.next(pipelineId);
  }

  getPipelineId(): number | null {
    return this.pipelineIdSubject.value;
  }

  setNavState(state: { [key: string]: boolean }) {
    this.navStateSource.next(state);
  }

  updateNavState(updates: { [key: string]: boolean }) {
    const currentState = this.navStateSource.value;
    this.setNavState({ ...currentState, ...updates });
  }

  setUploadedFile(file: File): void {
    this.uploadedFileSubject.next(file);

    this.setNavState({
      '/upload': false,
      '/config': false,
      '/preprocess': true,
      '/results': true,
      '/analysis': true,
      '/visualization': true,
      '/ai-models': true,
      '/algorithms': false,
    });
  }

  getUploadedFile(): File | null {
    return this.uploadedFileSubject.value;
  }

  setSamplingRate(rate: number): void {
    this.samplingRateSubject.next(rate);
  }

  getSamplingRate(): number {
    return this.samplingRateSubject.value;
  }

  setUploadedFileNameSubject(fileName: string): void {
    this.uploadedFileNameSubject.next(fileName);
  }

  getUploadedFileName(): string | null {
    return this.uploadedFileNameSubject.value;
  }

  setPreprocessingResult(result: any): void {
    this.preprocessingResult = result;
  }

  getPreprocessingResult(): any {
    return this.preprocessingResult;
  }

  setUploadedFileId(file: string | null): void {
    this.uploadedFileIdSubject.next(file);
  }

  getUploadedFileId(): string | null {
    return this.uploadedFileIdSubject.value as string | null;
  }

  setConfiguredFileId(id: string | null): void {
    this.configuredFileIdSubject.next(id);
  }

  getConfiguredFileId(): string | null {
    return this.configuredFileIdSubject.value as string | null;
  }

  setPreprocessingConfig(steps: AlgorithmStep[]): void {
    this.preprocessingConfigSubject.next(steps);
  }

  getPreprocessingConfig(): AlgorithmStep[] | null {
    return this.preprocessingConfigSubject.value;
  }

  setResultFileId(id: string | null): void {
    this.resultFileIdSubject.next(id);
  }

  getResultFileId(): string | null {
    return this.resultFileIdSubject.value;
  }

  setResultFileName(fileName: string | null): void {
    this.resultFileNameSubject.next(fileName);
  }

  getResultFileName(): string | null {
    return this.resultFileNameSubject.value;
  }

  setResultFileSize(fileSize: string): void {
    sessionStorage.setItem('resultFileSize', fileSize);
  }

  getResultFileSize(): string {
    return sessionStorage.getItem('resultFileSize') || '0 MB';
  }

  setProcessingTime(processingTime: string): void {
    sessionStorage.setItem('processingTime', processingTime);
  }

  getProcessingTime(): string {
    return sessionStorage.getItem('processingTime') || '0s';
  }

  setFigureOriginalData(figureOriginalData: string): void {
    sessionStorage.setItem('figureOriginalData', figureOriginalData);
  }

  getFigureOriginalData(): string | null {
    return sessionStorage.getItem('figureOriginalData');
  }

  setFigureProcessedData(figureProcessedData: string): void {
    sessionStorage.setItem('figureProcessedData', figureProcessedData);
  }

  getFigureProcessedData(): string | null {
    return sessionStorage.getItem('figureProcessedData');
  }

  setAnalysisResult(
    methodId: string,
    sourceType: 'uploaded' | 'result',
    fileId: string,
    result: AnalysisResult
  ): void {
    const key = `${methodId}_${sourceType}_${fileId}`;
    this.analysisCache.set(key, result);
  }

  getAnalysisResult(
    methodId: string,
    sourceType: 'uploaded' | 'result',
    fileId: string
  ): AnalysisResult | undefined {
    const key = `${methodId}_${sourceType}_${fileId}`;
    return this.analysisCache.get(key);
  }

  hasAnalysisResult(
    methodId: string,
    sourceType: 'uploaded' | 'result',
    fileId: string
  ): boolean {
    const key = `${methodId}_${sourceType}_${fileId}`;
    return this.analysisCache.has(key);
  }

  setDomainType(domainType: DomainType): void {
    this.domainTypeSubject.next(domainType);
  }

  getDomainType(): DomainType | null {
    return this.domainTypeSubject.value;
  }

  setConfigId(configId: string | null): void {
    this.configIdSubject.next(configId);
  }

  getConfigId(): string | null {
    return this.configIdSubject.value;
  }

  clearWorkflow(): void {
    this.uploadedFileSubject.next(null);
    this.preprocessingConfigSubject.next(null);
    this.uploadedFileIdSubject.next(null);
    this.configuredFileIdSubject.next(null);
    this.resultFileIdSubject.next(null);
    this.analysisCache.clear();
    this.preprocessingResult = null;
    this.fileConfigUIState = null;

    sessionStorage.removeItem('resultFileSize');
    sessionStorage.removeItem('processingTime');
    sessionStorage.removeItem('figureData');
    this.pipelineIdSubject.next(null);

    this.setNavState({
      '/upload': false,
      '/config': true,
      '/preprocess': true,
      '/results': true,
      '/analysis': true,
      '/visualization': true,
      '/ai-models': true,
      '/algorithms': false,
    });
  }

  resetNavStateAfterDeletingAllConfigs(): void {
    this.setNavState({
      '/upload': false,
      '/config': false,
      '/preprocess': true,
      '/results': true,
      '/analysis': true,
      '/visualization': true,
      '/ai-models': true,
      '/algorithms': false,
    });
  }

  /**
   * Clears analysis and processing results but KEEPS the original uploaded file.
   * Call this when the user changes configuration or wants to re-run preprocessing.
   */
  clearProcessingResults(): void {
    this.configuredFileIdSubject.next(null);
    this.resultFileIdSubject.next(null);

    this.analysisCache.clear();
    this.preprocessingResult = null;

    sessionStorage.removeItem('resultFileSize');
    sessionStorage.removeItem('processingTime');
    sessionStorage.removeItem('figureData');
    this.pipelineIdSubject.next(null);
  }

  setVisualizationState(state: {
    rawSubjects?: EEGSubjectData[];
    cleanSubjects?: EEGSubjectData[];
    dynamicPlots?: any[];
    rawData?: any;
    cleanData?: any;
    spectrogramRaw?: any[];
    spectrogramClean?: any[];
  }) {
    this.visualizationState = state;
  }

  getVisualizationState() {
    return this.visualizationState;
  }

  clearVisualizationState() {
    this.visualizationState = null;
  }

}
