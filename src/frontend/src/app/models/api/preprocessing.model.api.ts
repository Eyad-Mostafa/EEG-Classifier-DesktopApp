export enum DomainType {
  TIME = 'time',
  FREQUENCY = 'frequency',
  TIME_FREQUENCY = 'time_frequency',
  QUALITY = 'quality'
}

export interface SubjectFilter {
  subjectId: string;
  sessions: string[];
}

export interface SessionTrialsFilter {
  sessionId: string;
  trials: string[];
}

export interface SubjectTrialsFilter {
  subjectId: string;
  sessions: SessionTrialsFilter[];
}

export interface FilterRequest {
  subjects: SubjectTrialsFilter[];  
  labels: Record<string, number>;  
  channels: Record<string, string>;
  selected_channels?: Record<string, boolean>; 
  montage: string;
}

export interface AlgorithmStep {
  name: string;
  params: Record<string, any>;
}

export interface PreprocessRequest {
  file_id: string;
  samplingRate: number;
  pipeline: AlgorithmStep[];
}

export interface PreprocessResponse {
  status: string;
  result_id: string;
  file_name: string;
  sampling_rate: number;
  file_size_mb: number;
  processing_time: string;
  figure_data_original?: string | null;
  figure_data_processed?: string | null;
  summary: Record<string, any>;
  meta: Record<string, any>;
  domainType: DomainType;
  data_preview: Record<string, any>[];
}