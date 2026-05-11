export interface SessionTrialsSchema {
  sessionId: string;
  trials: string[];
}


export interface SubjectSessionTrialsSchema {
  subjectId: string;
  sessions: SessionTrialsSchema[];
}

export interface MetadataResponse {
  fileId: string;
  samplingRate: number;
  subjects: SubjectSessionTrialsSchema[];
  labels: number[];
  channels: string[];
}

export interface FilterResponse {
  status: string;
  tempFileId: string;
  n_rows: number;
  n_subjects: number;
}