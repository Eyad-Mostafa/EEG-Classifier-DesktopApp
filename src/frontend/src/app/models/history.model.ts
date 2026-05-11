export interface FileHistory {
    id: string;
    fileName: string;
    uploadDate: Date;
    samplingRate: number;
    duration: number;
    channels: number;
    fileSize: string;
    fileType: string;
}

export interface PreprocessingStep {
    name: string;
    parameters: Record<string, any>;
    order: number;
}

export interface AnalysisStep {
    type: string;
    name: string;
    parameters: Record<string, any>;
}

export interface VisualizationItem {
    type: string;
    title: string;
    config: Record<string, any>;
}

// NEW: Configuration interfaces based on your file-config.component.ts
export interface LabelConfig {
    [key: string]: string;  // e.g., { "0": "motor", "1": "imagery" }
}

export interface ChannelMapping {
    [key: string]: string;  // e.g., { "channel_1": "Fp1", "channel_2": "Fz" }
}

export interface SessionSelection {
    subjectId: string;
    sessions: string[];  // Selected session IDs
}

export interface FileConfiguration {
    labels: LabelConfig;
    channelMapping: ChannelMapping;
    selectedMontage: string;
    selectedSubjects: SessionSelection[];
    totalSubjectsSelected: number;
    totalSessionsSelected: number;
}

export interface FileHistoryDetail {
    fileId: string;
    fileName: string;
    samplingRate: number;
    preprocessing: PreprocessingStep[];
    analyses: AnalysisStep[];
    visualizations: VisualizationItem[];
    // NEW: Add configuration
    configuration?: FileConfiguration;
}

export interface UserHistory {
    files: FileHistory[];
    details: Map<string, FileHistoryDetail>;
}