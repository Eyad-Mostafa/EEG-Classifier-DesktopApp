import { AlgorithmInfo, AlgorithmParameterInfo } from '../api/algorithm-library.model.api';

export interface ParameterUI extends AlgorithmParameterInfo {
  hasError?: boolean;
  errorMessage?: string;
}

export interface AlgorithmUI extends Omit<AlgorithmInfo, 'parameters'> {
  enabled: boolean;
  isExpanded?: boolean;
  
  params: ParameterUI[]; 
}