export interface ConfigHistoryItem {
    config_id: string;
    file_id: string;
    configuration_json: {
        subjects: { subjectId: string; sessions: string[] }[];
        labels: Record<string, string>;
        channels: Record<string, string>;  // ← ADD THIS LINE
        selected_channels?: Record<string, boolean> | Array<{ id: string; name: string; label: string }>;
        montage: string;
    };
    created_at: string;
    last_opened_at:string;
}

export interface DeleteConfigHistoryResponse {
    message: string;
    file_id: string;
    deleted_count: number;
}

export interface DeleteSingleConfigResponse {
    message: string;
    file_id: string;
    config_id: string;
}