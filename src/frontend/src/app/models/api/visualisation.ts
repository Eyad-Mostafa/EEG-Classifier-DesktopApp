export interface VisualizationRequest {
  rawDataId: string | null;
  cleanDataId?: string | null;
  rawDataOnly: boolean;
  samplingRate: number;
  start?: number;
  duration?: number;
}

export interface EEGChannelData {
  [channelName: string]: number[];
}

export interface EEGTrialData {
  trialId: string;
  label: string;
  category?: string;
  time: number[];
  channels: EEGChannelData;
}

export interface EEGSessionData {
  sessionId: string;
  trials: EEGTrialData[];
}

export interface EEGSubjectData {
  subjectId: string;
  sessions: EEGSessionData[];
}

export interface VisualizationResponse {
  raw: EEGSubjectData[];
  clean?: EEGSubjectData[];
}

export interface SummaryResponse {
  rawSummary: { [key: string]: any };
  cleanSummary?: { [key: string]: any };
}

export interface SpectrogramData {
  times: number[];
  frequencies: number[];
  values: number[][];
}

export interface SpectrogramResponse {
  rawSpectrograms: SpectrogramData[];
  cleanSpectrograms?: SpectrogramData[];
}

export interface TrialMeta {
  trialFileId: string;
  trialPlotIndex: number;
  subject: string;
  session: string;
  label: string | number;
  category?: string | number;
  start: number;
  end: number;
}

export interface DynamicPlot {
  id: string;
  title: string;
  traces: Partial<Plotly.PlotData>[];
  layout: Partial<Plotly.Layout>;
  trialsMeta: TrialMeta[];
  trialsCount: number;
  filters: PlotFilterRequest;
}

export interface PlotFilterRequest {
  data_type: 'raw' | 'clean';
  subject_id: string;
  session_id: string;
  labels: string[];
  categories: string[];
  channels: string[];
}

export interface SavePlotRequest {
  config_id: string;
  plot_name: string;
  filters: PlotFilterRequest;
}

export interface SavePlotResponse {
  success: boolean;
  action?: 'created' | 'updated';
  plot_id: number;
  config_id: number;
}

export interface GetPlotsResponse {
  plot_id: number;
  config_id: number;
  plot_name: string;
  filters_json: PlotFilterRequest;
  created_at?: string;
}
