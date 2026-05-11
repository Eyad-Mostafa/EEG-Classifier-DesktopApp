import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigService } from '../services/config.service';
import {
  VisualizationRequest,
  VisualizationResponse,
  SummaryResponse,
  SpectrogramResponse,
  SavePlotResponse,
  SavePlotRequest,
  GetPlotsResponse,
} from '../models/api/visualisation';

@Injectable({
  providedIn: 'root',
})
export class VisualizationService {
  private visualizationUrl: string;

  constructor(
    private http: HttpClient,
    private configService: ConfigService,
  ) {
    this.visualizationUrl = `${this.configService.getApiUrl()}/visualization`;
  }

  getVisualization(
    payload: VisualizationRequest,
  ): Observable<VisualizationResponse> {
    return this.http.post<VisualizationResponse>(
      `${this.visualizationUrl}`,
      payload,
    );
  }

  getVisualizationSummary(
    payload: VisualizationRequest,
  ): Observable<SummaryResponse> {
    return this.http.post<SummaryResponse>(
      `${this.visualizationUrl}/summary`,
      payload,
    );
  }

  getSpectrogram(
    payload: VisualizationRequest,
  ): Observable<SpectrogramResponse> {
    return this.http.post<SpectrogramResponse>(
      `${this.visualizationUrl}/spectrogram`,
      payload,
    );
  }

  savePlot(payload: SavePlotRequest): Observable<SavePlotResponse> {
    return this.http.post<SavePlotResponse>(
      `${this.visualizationUrl}/add-plot`,
      payload,
    );
  }
  getPlots(configId: string): Observable<GetPlotsResponse[]> {
    const params = new HttpParams().set('config_id', configId.toString());
    return this.http.get<GetPlotsResponse[]>(
      `${this.visualizationUrl}/get-plots`,
      { params },
    );
  }

  deletePlot(plotId: number): Observable<{ success: boolean }> {
    return this.http.delete<{ success: boolean }>(
      `${this.visualizationUrl}/plot/${plotId}`,
    );
  }

  deleteAllPlots(configId: string): Observable<void> {
    return this.http.delete<void>(`${this.visualizationUrl}/plots/all/${configId}`);
  }
}
