import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';
import { catchError } from 'rxjs/operators';
import { ConfigService } from './config.service';

import {
  AnalysisModule,
  AnalysisRequest,
  AnalysisResponse,
  AnalysisHistoryRequest,
  AnalysisHistoryResponse
} from '../models/api/analysis.api';

@Injectable({
  providedIn: 'root'
})
export class AnalysisService {
  private analysisApiUrl: string;

  constructor(private http: HttpClient, private configService: ConfigService) {
    this.analysisApiUrl = `${this.configService.getApiUrl()}/analysis`;
  }

  getAllAnalysisMethods(): Observable<AnalysisModule[]> {
    return this.http.get<AnalysisModule[]>(`${this.analysisApiUrl}/methods`).pipe(
      catchError(error => {
        console.error('Error fetching analysis methods:', error);
        return of([]);
      })
    );
  }

  runAnalysis(
    methodId: string,
    fileId: string,
    configId: string,
    pipelineId: number | null,
    sourceType: 'configured' | 'preprocessed',
    samplingRate: number,
    parameters?: Record<string, any> | null
  ): Observable<AnalysisResponse> {
    const payload: AnalysisRequest = {
      method_id: methodId,
      file_id: fileId,
      config_id: configId,
      pipeline_id: pipelineId,
      source_type: sourceType,
      samplingRate: samplingRate,
      parameters: parameters || {}
    };

    return this.http.post<AnalysisResponse>(`${this.analysisApiUrl}/run`, payload).pipe(
      catchError(error => {
        console.error('Error running analysis:', error);
        throw error;
      })
    );
  }

  getAnalysisHistory(
    configId: string,
    pipelineId: number | null,
    sourceType: 'configured' | 'preprocessed'
  ): Observable<AnalysisHistoryResponse> {
    const payload: AnalysisHistoryRequest = {
      config_id: configId,
      pipeline_id: pipelineId,
      source_type: sourceType
    };

    return this.http.post<AnalysisHistoryResponse>(`${this.analysisApiUrl}/history`, payload).pipe(
      catchError(error => {
        console.error('Error fetching analysis history:', error);
        return of({ items: [] });
      })
    );
  }
}