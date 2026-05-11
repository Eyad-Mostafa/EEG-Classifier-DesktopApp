import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  ConfigHistoryItem,
  DeleteConfigHistoryResponse,
  DeleteSingleConfigResponse,
} from '../models/api/config-history.model.api';

import { MetadataResponse, FilterResponse } from '../models/api/metadata.model.api';
import { FilterRequest } from '../models/api/preprocessing.model.api';
import { ConfigService } from './config.service';

@Injectable({ providedIn: 'root' })
export class EegDataService {
  private fileInfoUrl: string;

  constructor(private http: HttpClient, private configService: ConfigService) {
    this.fileInfoUrl = `${this.configService.getApiUrl()}/file-info`;
  }

  getFileMetadata(fileId: string): Observable<MetadataResponse> {
    return this.http.get<MetadataResponse>(
      `${this.fileInfoUrl}/${fileId}/metadata`
    );
  }

  // ✅ Use strict type 'FilterRequest' instead of 'any'
  filterFile(fileId: string, body: FilterRequest): Observable<FilterResponse> {
    return this.http.post<FilterResponse>(
      `${this.fileInfoUrl}/filter/${fileId}`,
      body
    );
  }

  getFileConfigHistory(fileId: string): Observable<ConfigHistoryItem[]> {
    return this.http.get<ConfigHistoryItem[]>(
      `${this.fileInfoUrl}/${fileId}/config-history`
    );
  }

  deleteFileConfigHistory(
    fileId: string
  ): Observable<DeleteConfigHistoryResponse> {
    return this.http.delete<DeleteConfigHistoryResponse>(
      `${this.fileInfoUrl}/${fileId}/config-history`
    );
  }

  deleteSingleFileConfig(
    fileId: string,
    configId: string
  ): Observable<DeleteSingleConfigResponse> {
    return this.http.delete<DeleteSingleConfigResponse>(
      `${this.fileInfoUrl}/${fileId}/config-history/${configId}`
    );
  }

}