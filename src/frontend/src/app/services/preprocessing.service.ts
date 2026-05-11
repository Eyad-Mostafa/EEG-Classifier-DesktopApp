import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

import { PreprocessResponse, PreprocessRequest, AlgorithmStep } from '../models/api/preprocessing.model.api';
import { ConfigService } from './config.service';

@Injectable({
  providedIn: 'root',
})
export class PreprocessingService {
  private apiUrl: string;

  constructor(
    private http: HttpClient,
    private configService: ConfigService
  ) {
    this.apiUrl = `${this.configService.getApiUrl()}/preprocess/`;
  }

  runPreprocessing(fileId: string, samplingRate: number, pipeline: AlgorithmStep[]): Observable<PreprocessResponse> {
    const payload: PreprocessRequest = {
      file_id: fileId,
      samplingRate: samplingRate,
      pipeline: pipeline
    };

    return this.http.post<PreprocessResponse>(this.apiUrl, payload);
  }

  downloadResult(fileId: string) {
    return this.http.get(
      `${this.apiUrl}download/${fileId}`,
      {
        responseType: 'blob',
        observe: 'response'
      }
    );
  }
}