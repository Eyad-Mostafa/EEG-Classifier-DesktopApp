export interface UploadResponse {
  status: string;
  filename: string;
  file_id: string;
}

export interface UploadHistoryItem {
  file_id: string;
  filename: string;
  sampling_rate: number;
  file_path: string;
  first_opened_time: string;
  last_opened_at:string;
}