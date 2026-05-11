import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { AiModel, FileLabelInfo, InferenceRequest, InferenceResponse } from '../models/api/ai-models.model';
import { ConfigService } from './config.service';

@Injectable({
  providedIn: 'root'
})
export class AiModelsService {
  constructor(
    private http: HttpClient,
    private configService: ConfigService
  ) { }

  getAvailableModels(): Observable<AiModel[]> {
    return this.http.get<AiModel[]>(`${this.configService.getApiUrl()}/ai-models/`);
  }

  runInference(request: InferenceRequest): Observable<InferenceResponse> {
    return this.http.post<InferenceResponse>(`${this.configService.getApiUrl()}/ai-models/predict`, request);
  }

  getFileLabels(configId: string): Observable<FileLabelInfo> {
    return this.http.get<FileLabelInfo>(
      `${this.configService.getApiUrl()}/ai-models/file-labels/${configId}`
    );
  }

  downloadCSV(resultId: string): Observable<Blob> {
    return this.http.get(`${this.configService.getApiUrl()}/ai-models/download/${resultId}`, {
      responseType: 'blob'
    });
  }
  getImageUrl(url?: string): string {
    if (!url) return 'assets/images/model-placeholder.png';
    if (url.startsWith('http')) return url;

    // Get base URL dynamically from config service
    let apiUrl = this.configService.getApiUrl();

    // Remove /api from the end if it exists (to avoid duplication)
    apiUrl = apiUrl.replace(/\/api$/, '');

    // Clean the image path
    const cleanUrl = url.replace(/^\//, '');

    // Build the full URL
    return `${apiUrl}/api/static/models/${cleanUrl}`;
  }
}