// app/models/pipeline.model.ts

import { DomainType } from './api/preprocessing.model.api';

export interface SavedPipeline {
    id: string;
    name: string;
    type: 'global' | 'file-specific';
    fileId?: string; // Only for file-specific
    fileName?: string; // Only for file-specific
    createdAt: Date;
    notes?: string; // ADD THIS - user notes about the pipeline
    config: {
        algorithms: any[]; // The AlgorithmUI array from preprocessing
        selectedDomain: DomainType;
    };
}

export interface PipelineSummary {
    id: string;
    name: string;
    type: 'global' | 'file-specific';
    createdAt: Date;
    algorithmCount: number;
    fileName?: string;
    notes?: string; // ADD THIS - preview of notes
}