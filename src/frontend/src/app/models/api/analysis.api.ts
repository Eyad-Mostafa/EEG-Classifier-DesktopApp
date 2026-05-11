import { DomainType } from "./preprocessing.model.api";

export interface AnalysisRequest {
  method_id: string;
  file_id: string;
  config_id: string;
  pipeline_id?: number | null;
  source_type: 'configured' | 'preprocessed';
  samplingRate: number;
  parameters?: Record<string, any> | null;
}

export interface AnalysisResult {
  summary: Record<string, any>;
  analysis_data: any[] | Record<string, any> | null;
  visualization_data?: Record<string, any> | null;
}

export interface AnalysisResponse {
  method_id: string;
  success: boolean;
  result: AnalysisResult;
}

export interface ErrorResponse {
  detail: string;
}

export interface AnalysisModule {
  id: string;
  name: string;
  description: string;
  category: string;
  type: string;
  parameters?: any[];
  allowedDomainTypes: DomainType[];
  howItWorks?: string;
  useCases?: string[];
}

export interface AnalysisHistoryRequest {
  config_id: string;
  pipeline_id?: number | null;
  source_type: 'configured' | 'preprocessed';
}

export interface AnalysisHistoryItem {
  method_id: string;
  analysis_run_id: number;
  executed_at?: string | null;
  result: AnalysisResult;
}

export interface AnalysisHistoryResponse {
  items: AnalysisHistoryItem[];
}