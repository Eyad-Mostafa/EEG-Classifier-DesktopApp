export interface AiModelRequirements {
  num_channels: number;
  time_points: number;
  sampling_rate: number;
  domain: string;
}

export interface AiModel {
  files: any;
  id: string;
  name: string;
  description: string;
  accuracy: number;
  architecture: string;
  requirements: {
    num_channels: number;
    time_points: number;
    sampling_rate: number;
    domain: string;
  };
  classes: string[];
  image_url?: string;
  
  preprocessing_names?: string[]; 
}

export interface InferenceRequest {
  model_id: string;
  config_id: string;
  apply_preprocessing?: boolean
  label_mapping?: Record<string, string>;
}

export interface PredictionItem {
  subject: string;
  session: string;
  trial: number;
  predictedClass: string;
  confidence: number;
  trueClass?: string;
  correct?: boolean;
}

export interface PerClassMetric {
  precision: number;
  recall: number;
  f1: number;
  support: number;
}

export interface InferenceMetrics {
  accuracy: number;
  f1_score: number;
  precision: number;
  recall: number;
  per_class: Record<string, PerClassMetric>;
}

export interface InferenceSummary {
  total_trials_analyzed: number;
  class_distribution: { [className: string]: number };
  average_confidence: number;
  metrics?: InferenceMetrics;
}

export interface FileLabelInfo {
  labels: number[];
  detailed_labels: Record<string, number>;
}

export interface InferenceResponse {
  status: string;
  model_used: string;
  result_id?: string;
  summary: InferenceSummary;
  predictions: PredictionItem[];
}