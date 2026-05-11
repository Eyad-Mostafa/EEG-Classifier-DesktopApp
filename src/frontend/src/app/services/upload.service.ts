import { Injectable } from '@angular/core';
import { HttpClient, HttpEvent, HttpEventType, HttpErrorResponse } from '@angular/common/http';
import { Observable, throwError } from 'rxjs';
import { catchError, map } from 'rxjs/operators';
import { UploadHistoryItem, UploadResponse } from '../models/api/upload.model.api';
import { ConfigService } from './config.service';

@Injectable({
  providedIn: 'root',
})
export class UploadService {
  private uploadUrl: string;
  private sampleCsvUrl: string;
  
  constructor(private http: HttpClient, private configService: ConfigService) {
    this.uploadUrl = `${this.configService.getApiUrl()}/upload`;
    this.sampleCsvUrl = `${this.configService.getApiUrl()}/preprocess/sample-csv`;
  }

  // Accepts either an HTML5 File object (from Electron) OR a raw string path (from Dev Panel)
  uploadFile(fileOrPath: File | string, sampleRate: number): Observable<number | UploadResponse> {
    const formData = new FormData();
    let filePath = '';

    // 1. Determine where the path is coming from
    if (typeof fileOrPath === 'string') {
      // Manual path entry
      filePath = fileOrPath;
    } else {
      // Electron File object extraction
      if ((window as any).electronAPI && (window as any).electronAPI.getFilePath) {
        filePath = (window as any).electronAPI.getFilePath(fileOrPath);
      } else {
        filePath = (fileOrPath as any).path;
      }
    }

    // 2. Safety check
    if (!filePath) {
      return throwError(() => new Error('Could not find absolute file path. Ensure you are running inside Electron or use the Manual Path tool.'));
    }

    // 3. Append to FormData
    formData.append('file_path', filePath);
    formData.append('sample_rate', sampleRate.toString());

    return this.http
      .post<UploadResponse>(this.uploadUrl, formData, {
        reportProgress: true,
        observe: 'events',
      })
      .pipe(
        map((event: HttpEvent<any>) => {
          switch (event.type) {
            case HttpEventType.UploadProgress:
              return Math.round((100 * event.loaded) / (event.total ?? 1));
            case HttpEventType.Response:
              return event.body as UploadResponse;
            default:
              return 0;
          }
        }),
        catchError(this.handleError)
      );
  }

  getUploadHistory(): Observable<UploadHistoryItem[]> {
    return this.http.get<UploadHistoryItem[]>(`${this.configService.getApiUrl()}/upload/history`).pipe(
      catchError(this.handleError)
    );
  }

  downloadSampleFile(): Observable<Blob> {
    return this.http.get(this.sampleCsvUrl, { responseType: 'blob' }).pipe(
      catchError(this.handleError)
    );
  }

  deleteHistoryFile(fileId: string): Observable<any> {
    return this.http.delete(`${this.configService.getApiUrl()}/upload/${fileId}`).pipe(
      catchError(this.handleError)
    );
  }

  deleteAllHistory(): Observable<any> {
    return this.http.delete(`${this.configService.getApiUrl()}/upload/`);
  }

  private handleError(error: HttpErrorResponse) {
    let message = 'An unknown error occurred';
    if (error.error?.detail) {
      message = error.error.detail;
    } else if (error.status === 0) {
      message = 'Cannot connect to the backend server';
    }
    return throwError(() => new Error(message));
  }
}