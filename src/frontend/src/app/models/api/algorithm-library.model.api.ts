export type AlgorithmCategory = string;

export type AlgorithmType = 'preprocessing' | 'analysis';

export type ParameterType = 'string' | 'number' | 'boolean' | 'array';

import { DomainType } from "./preprocessing.model.api";

// 2. Define the Parameter Structure
export interface AlgorithmParameterInfo {
  name: string;
  type: ParameterType;
  value: any;           // Current value (usually same as default initially)
  default: any;
  min?: number | null;  // Optional because string params don't have min
  max?: number | null;
  options?: string[] | null; // For dropdowns
  required: boolean;
  description: string;
}

// 3. Define the Unified Algorithm Model
export interface AlgorithmInfo {
  id: string;
  name: string;
  category: string;
  description: string;
  
  type: AlgorithmType; 
  
  domainType?: DomainType;
  
  parameters: AlgorithmParameterInfo[];
  
  examples?: any[];
  howItWorks?: string;
  useCases?: string[];
  relatedAlgorithms?: string[];
}