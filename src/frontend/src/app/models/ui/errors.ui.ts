export interface ParameterErrorDetails {
  parameter: string;
  value: any;
  constraints: {
    required?: boolean;
    type?: string;
    min?: number;
    max?: number;
    options?: any[];
  };
}

export interface PreprocessingError {
  title: string;
  message: string;
  details?: string;
  status?: number;
  timestamp?: string;
  showRetry: boolean;
  parameterDetails?: ParameterErrorDetails;
  errorType?: string;
}