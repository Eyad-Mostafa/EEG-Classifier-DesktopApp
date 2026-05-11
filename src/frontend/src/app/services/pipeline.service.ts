import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { SavedPipeline, PipelineSummary } from '../models/pipeline.model';
import { DomainType } from '../models/api/preprocessing.model.api';
import { AlgorithmInfo } from '../models/api/algorithm-library.model.api';
import { ConfigService } from './config.service';
import { WorkflowService } from './workflow.service';
export interface StepModel {
  name: string;
  params: { [key: string]: any };
}

@Injectable({
  providedIn: 'root',
})
export class PipelineService {
  private readonly API_URL: string;
  private allAlgorithms: AlgorithmInfo[] = [];

  constructor(
    private http: HttpClient,
    private configService: ConfigService,
    private workflowService: WorkflowService
  ) {
    this.API_URL = this.configService.getApiUrl() + '/pipelines';
  }

  setAlgorithms(algorithms: AlgorithmInfo[]): void {
    this.allAlgorithms = algorithms;
    console.log('PipelineService: Stored', algorithms.length, 'algorithms');
  }

  async getPipelineSummaries(
    type: 'global' | 'file-specific',
    fileId?: string,
  ): Promise<PipelineSummary[]> {
    try {
      let response;

      if (type === 'global') {
        response = await firstValueFrom(
          this.http.get<any[]>(`${this.API_URL}/global`),
        );
      } else {
        if (!fileId) {
          return [];
        }
        response = await firstValueFrom(
          this.http.get<any[]>(`${this.API_URL}/file/${fileId}`),
        );
      }

      console.log(`Loaded ${response.length} ${type} pipelines:`, response);

      return response.map((p) => ({
        id: p.pipeline_id.toString(),
        name: p.pipeline_name,
        type: type,
        createdAt: new Date(p.executed_at),
        algorithmCount: p.algorithm_count || p.pipeline?.length || 0,
        fileName: p.file_name,
        notes: p.notes,
      }));
    } catch (error) {
      console.error('Failed to load pipelines:', error);
      return [];
    }
  }

  async savePipeline(
    name: string,
    type: 'global' | 'file-specific',
    config: any,
    currentFileId?: string,
    currentFileName?: string,
    notes?: string,
  ): Promise<SavedPipeline> {
    const steps = this.convertConfigToSteps(config);

    if (steps.length === 0) {
      throw new Error('No enabled algorithms to save');
    }

    const payload = {
      pipeline_name: name,
      is_template: type === 'global',
      config_id: type === 'file-specific' ? currentFileId : null,
      file_name: type === 'file-specific' ? currentFileName : null,
      pipeline: steps,
      notes: notes || '',
    };

    console.log(
      '🔵 SAVING PIPELINE - Full payload:',
      JSON.stringify(payload, null, 2),
    );

    const response = await firstValueFrom(
      this.http.post<{
        pipeline_id: number;
        message: string;
        steps_saved: number;
        config_id?: number;
      }>(`${this.API_URL}/save`, payload),
    );

    console.log('🔵 SAVE RESPONSE:', response);

    return {
      id: response.pipeline_id.toString(),
      name: name,
      type: type,
      createdAt: new Date(),
      notes: notes || '',
      config: config,
      ...(type === 'file-specific' && {
        fileId: currentFileId,
        fileName: currentFileName,
      }),
    };
  }

  async autoSavePipeline(
    config: any,
    fileId: string,
    fileName: string,
  ): Promise<SavedPipeline> {
    const steps = this.convertConfigToSteps(config);
    const autoName = `${fileName} - ${new Date().toLocaleString()}`;

    if (steps.length === 0) {
      throw new Error('No enabled algorithms to auto-save');
    }

    const payload = {
      pipeline_name: autoName,
      is_template: false,
      config_id: fileId,
      file_name: fileName,
      pipeline: steps,
      notes: `Auto-saved on ${new Date().toLocaleString()}`,
    };

    const response = await firstValueFrom(
      this.http.post<{
        pipeline_id: number;
        message: string;
        config_id?: number;
      }>(`${this.API_URL}/auto-save`, payload),
    );

    return {
      id: response.pipeline_id.toString(),
      name: autoName,
      type: 'file-specific',
      createdAt: new Date(),
      notes: 'Auto-saved',
      config: config,
      fileId: fileId,
      fileName: fileName,
    };
  }

  async loadPipeline(id: string): Promise<SavedPipeline | undefined> {
    try {
      const response = await firstValueFrom(
        this.http.get<any>(`${this.API_URL}/load/${id}`),
      );

      console.log('Load pipeline response:', response);
      return this.convertBackendToSavedPipeline(response);
    } catch (error) {
      console.error('Failed to load pipeline:', error);
      return undefined;
    }
  }

  async deletePipeline(id: string): Promise<void> {
    try {
      await firstValueFrom(this.http.delete(`${this.API_URL}/delete/${id}`));
      this.workflowService.setPipelineId(null);
      console.log('Pipeline deleted:', id);
    } catch (error) {
      console.error('Failed to delete pipeline:', error);
      throw error;
    }
  }

  private convertConfigToSteps(config: any): StepModel[] {
    const steps: StepModel[] = [];

    const enabledAlgorithms = config.algorithms.filter(
      (algo: any) =>
        algo.enabled === true && algo.domainType === config.selectedDomain,
    );

    console.log(
      `Converting ${enabledAlgorithms.length} enabled algorithms to steps`,
    );

    for (const algorithm of enabledAlgorithms) {
      const params: { [key: string]: any } = {};

      if (algorithm.params) {
        for (const param of algorithm.params) {
          if (param.value !== undefined && param.value !== '') {
            params[param.name] = param.value;
          }
        }
      }

      steps.push({
        name: algorithm.id,
        params: params,
      });
    }

    return steps;
  }

  private convertBackendToSavedPipeline(backend: any): SavedPipeline {
    const algorithms = backend.steps.map((step: any) => {
      const originalAlgorithm = this.allAlgorithms.find(
        (algo) => algo.id === step.name,
      );

      const paramsArray = Object.entries(step.params || {}).map(
        ([key, value]) => ({
          name: key,
          value: value,
          hasError: false,
          errorMessage: '',
        }),
      );

      return {
        id: step.name,
        name: step.name,
        enabled: true,
        description: originalAlgorithm?.description || '',
        domainType: originalAlgorithm?.domainType || DomainType.TIME,
        params: paramsArray,
        isExpanded: false,
      };
    });

    let selectedDomain = DomainType.TIME;
    if (algorithms.length > 0 && algorithms[0].domainType) {
      selectedDomain = algorithms[0].domainType;
    }

    return {
      id: backend.pipeline_id.toString(),
      name: backend.pipeline_name,
      type: backend.is_template ? 'global' : 'file-specific',
      createdAt: new Date(backend.executed_at),
      notes: backend.notes || '',
      fileId: backend.file_id,
      fileName: backend.file_name,
      config: {
        algorithms: algorithms,
        selectedDomain: selectedDomain,
      },
    };
  }
  // Add this method to PipelineService class

  async deleteAllPipelines(type: 'global' | 'file-specific', configId?: string): Promise<void> {
    try {
      if (type === 'global') {
        await firstValueFrom(this.http.delete(`${this.API_URL}/delete-all/global`));
      } else {
        if (!configId) {
          throw new Error('configId required for file-specific delete');
        }
        await firstValueFrom(this.http.delete(`${this.API_URL}/delete-all/file/${configId}`));
      }
      this.workflowService.setPipelineId(null);
      console.log('All pipelines deleted:', type);
    } catch (error) {
      console.error('Failed to delete all pipelines:', error);
      throw error;
    }
  }
}
