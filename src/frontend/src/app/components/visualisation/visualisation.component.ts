import {
  Component,
  AfterViewInit,
  OnInit,
  OnDestroy,
  NgZone,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Subscription, forkJoin } from 'rxjs';

import { VisualizationService } from '../../services/visualization.service';
import { WorkflowService } from '../../services/workflow.service';
import { RouterLink } from '@angular/router';

import { AppLoaderComponent } from '../ui/app-loader/app-loader.component';
import { ThemeService } from '../../services/theme.service';

import {
  DynamicPlot,
  EEGChannelData,
  EEGSubjectData,
  EEGTrialData,
  PlotFilterRequest,
  SavePlotRequest,
  SpectrogramData,
  TrialMeta,
  VisualizationRequest,
  VisualizationResponse,
} from '../../models/api/visualisation';

import * as Plotly from 'plotly.js-dist-min';
import {
  HistoryPanelComponent,
  SavedPlotItem,
} from '../visualisation/history-panel/history-panel.component';

@Component({
  selector: 'app-visualization',
  standalone: true,
  imports: [
    FormsModule,
    CommonModule,
    AppLoaderComponent,
    RouterLink,
    HistoryPanelComponent,
  ],
  templateUrl: './visualisation.component.html',
  styleUrls: [],
})
export class VisualizationComponent
  implements OnInit, AfterViewInit, OnDestroy
{
  loading = false;
  maxTime = 60;

  rawSubjects!: EEGSubjectData[];
  cleanSubjects?: EEGSubjectData[];

  rawData?: { time: number[]; channels: EEGChannelData };
  cleanData?: { time: number[]; channels: EEGChannelData };

  rawFileId = '';
  cleanFileId = '';
  isFilePreprocessed = this.workflowService.getResultFileId() ? true : false;

  selectedChannelForRaw = 0;
  selectedChannelForClean = 0;

  spectrogramDataRaw: SpectrogramData[] = [];
  spectrogramDataClean: SpectrogramData[] = [];

  isAddPlotModalOpen = false;
  dynamicPlots: DynamicPlot[] = [];

  // UI state
  showAddPlotModal = false;

  // data source toggle
  selectedDataType: 'raw' | 'clean' = 'raw';

  // selections
  selectedSubjectId?: string;
  selectedSessionId?: string;

  selectedTrials: string[] = [];
  selectedChannels: string[] = [];

  // derived lists (from response)
  availableSubjects: string[] = [];
  availableSessions: string[] = [];
  availableTrials: EEGTrialData[] = [];
  availableChannels: string[] = [];

  availableLabels: string[] = [];
  selectedLabels: string[] = [];

  availableCategories: string[] = [];
  selectedCategories: string[] = [];

  isSaveModalOpen = false;
  savePlotName = '';
  selectedPlotToSave: any = null;

  showHistoryPanel = false;
  historyItems: SavedPlotItem[] = [];

  plotStatusMessage = '';
  plotStatusType: 'success' | 'error' | 'info' = 'success';
  private plotStatusTimer: any = null;

  errorMessage = '';

  private themeSubscription?: Subscription;

  private readonly MAX_POINTS = 30000;

  get isDarkMode(): boolean {
    return document.documentElement.classList.contains('dark');
  }

  currentIsDark = this.isDarkMode;

  constructor(
    private visualizationService: VisualizationService,
    private workflowService: WorkflowService,
    private themeService: ThemeService,
    private ngZone: NgZone, // Inject NgZone
  ) {}

  ngOnInit(): void {
    this.loading = true;
    this.handleNavbar();
  }

  ngAfterViewInit(): void {
    this.themeSubscription = this.themeService.isDarkMode$.subscribe(
      (isDark) => {
        console.log('Theme changed to:', isDark ? 'dark' : 'light');
        this.currentIsDark = isDark;
        // Only update if data is loaded
        if (!this.loading && this.rawSubjects) {
          this.updatePlotsTheme(isDark);
        }
      },
    );

    this.rawFileId = this.workflowService.getConfiguredFileId() ?? '';
    this.cleanFileId = this.workflowService.getResultFileId() ?? '';

    if (!this.rawFileId) {
      console.warn('No EEG files uploaded yet.');
      this.loading = false;
      return;
    }

    // Wait for DOM to stabilize
    setTimeout(() => this.fetchData(), 100);
  }

  ngOnDestroy(): void {
    if (this.themeSubscription) {
      this.themeSubscription.unsubscribe();
    }
  }

  fetchData() {
    const payload: VisualizationRequest = {
      rawDataId: this.rawFileId,
      cleanDataId: this.cleanFileId,
      rawDataOnly: !this.isFilePreprocessed,
      samplingRate: this.workflowService.getSamplingRate(),
    };

    forkJoin({
      vis: this.visualizationService.getVisualization(payload),
      spec: this.visualizationService.getSpectrogram(payload),
    }).subscribe({
      next: ({ vis, spec }) => {
        this.rawSubjects = vis.raw;
        this.cleanSubjects = vis.clean;
        this.rawData = this.flattenForInitialPlot(this.rawSubjects);
        if (this.cleanSubjects) {
          this.cleanData = this.flattenForInitialPlot(this.cleanSubjects);
        }
        this.availableSubjects = this.getSubjects();
        console.log('Available subjects:', this.availableSubjects);
        this.availableChannels = Object.keys(
          vis.raw[0].sessions[0].trials[0].channels,
        );
        this.availableLabels = [];
        this.availableCategories = this.getAllCategories(vis);

        this.selectedLabels = [];
        this.selectedCategories = [...this.availableCategories];
        this.selectedChannels = [...this.availableChannels];

        // if (this.rawData.time.length > 0) {
        //   this.maxTime = this.rawData.time[this.rawData.time.length - 1];
        // }

        this.spectrogramDataRaw = spec.rawSpectrograms;
        this.spectrogramDataClean = spec.cleanSpectrograms || [];

        const configId = this.workflowService.getConfiguredFileId();
        if (!configId) {
          console.error('No configured file id available');
          return;
        }
        this.loadSavedPlots(configId);

        this.loading = false;

        this.ngZone.runOutsideAngular(() => {
          setTimeout(() => {
            this.updateRawDataPlot(true);
            this.updateCleanedDataPlot(true);

            this.selectedChannelForRaw = 0;
            this.selectedChannelForClean = 0;
            this.plotRawSpectrogram(0, true);
            this.plotCleanSpectrogram(0, true);
          }, 100);
        });
      },
      error: (err) => {
        console.error(err);
        this.loading = false;
      },
    });
  }

  loadSavedPlots(configId: string): void {
    this.visualizationService.getPlots(configId).subscribe({
      next: (plots) => {
        this.historyItems = plots.map((plot) => ({
          plot_id: plot.plot_id,
          file_id: plot.config_id,
          plot_name: plot.plot_name,
          created_at: plot.created_at ? new Date(plot.created_at) : new Date(),
          filter_json: this.normalizeFilters(plot.filters_json),
        }));

        console.log('historyItems:', this.historyItems);
        console.log('first filter_json:', this.historyItems[0]?.filter_json);
      },
      error: (err) => {
        console.error('Failed to load saved plots', err);
      },
    });
  }

  private downsample(data: number[], targetCount: number): number[] {
    const length = data.length;
    // If we have fewer points than pixels, just show everything. No need to compress.
    if (length <= targetCount) return data;

    // 1. Define the "Bucket" size
    // If we have 10,000 points and want 1,000 dots, our bucket size is 10.
    // We process the data in chunks of 10 points at a time.
    const bucketSize = Math.floor(length / targetCount);
    const sampled: number[] = [];

    // 2. Loop through the buckets
    for (let i = 0; i < length; i += bucketSize) {
      // 3. Grab the raw points for this bucket
      // e.g., data[0] to data[9]
      const chunk = data.slice(i, i + bucketSize);

      if (chunk.length > 0) {
        // 4. Find the Extremes
        // We don't care about the middle points, just the top and bottom limits.
        const min = Math.min(...chunk);
        const max = Math.max(...chunk);

        // 5. Save BOTH
        // By plotting both, the line graph will draw a vertical line
        // covering the full range of movement for this time period.
        sampled.push(min);
        sampled.push(max);
      }
    }
    return sampled;
  }

  // --- PLOTTING HELPERS ---

  private getPlotConfig() {
    return {
      responsive: true,
      displayModeBar: true,
      displaylogo: false,
      scrollZoom: false,
    };
  }

  private getBaseLayout(
    title: string,
    isDark: boolean = this.currentIsDark,
  ): Partial<Plotly.Layout> {
    const textColor = isDark ? '#f1f5f9' : '#111827';
    const bgColor = isDark ? '#1e293b' : '#ffffff';
    const gridColor = isDark ? '#334155' : '#e2e8f0';

    return {
      uirevision: 'keep-zoom',
      title: { text: title, font: { color: textColor } },
      autosize: true,
      margin: { t: 40, b: 40, l: 50, r: 20 },
      paper_bgcolor: bgColor,
      plot_bgcolor: bgColor,
      font: { color: textColor },
      xaxis: {
        rangeslider: { visible: false },
        showgrid: true,
        gridcolor: gridColor,
        zerolinecolor: gridColor,
        color: textColor,
      },
      yaxis: {
        showgrid: true,
        gridcolor: gridColor,
        zerolinecolor: gridColor,
        color: textColor,
      },
      legend: { font: { color: textColor }, bgcolor: 'rgba(0,0,0,0)' },
    };
  }

  updatePlotsTheme(isDark: boolean = this.currentIsDark) {
    this.currentIsDark = isDark;

    this.ngZone.runOutsideAngular(() => {
      this.updateRawDataPlot(false, isDark);
      this.updateCleanedDataPlot(false, isDark);

      if (this.spectrogramDataRaw.length > 0) {
        this.plotRawSpectrogram(this.selectedChannelForRaw, false, isDark);
      }

      if (this.spectrogramDataClean.length > 0) {
        this.plotCleanSpectrogram(this.selectedChannelForClean, false, isDark);
      }

      this.updateDynamicPlotsTheme(isDark);
    });
  }

  updateDynamicPlotsTheme(isDark: boolean = this.currentIsDark) {
    this.dynamicPlots.forEach((plot) => {
      const themedLayout = this.getBaseLayout(plot.title, isDark);

      const updatedLayout: Partial<Plotly.Layout> = {
        ...plot.layout,
        paper_bgcolor: themedLayout.paper_bgcolor,
        plot_bgcolor: themedLayout.plot_bgcolor,
        font: themedLayout.font,
        title: themedLayout.title,
        xaxis: {
          ...(plot.layout.xaxis || {}),
          ...(themedLayout.xaxis || {}),
        },
        yaxis: {
          ...(plot.layout.yaxis || {}),
          ...(themedLayout.yaxis || {}),
        },
        legend: {
          ...(plot.layout.legend || {}),
          ...(themedLayout.legend || {}),
        },
      };

      plot.layout = updatedLayout;
      Plotly.react(plot.id, plot.traces, updatedLayout, this.getPlotConfig());
    });
  }

  updateRawDataPlot(isInit = false, isDark: boolean = this.currentIsDark) {
    if (!this.rawData) return;

    const sampledTime = this.downsample(this.rawData.time, this.MAX_POINTS);

    const rawTraces: Partial<Plotly.PlotData>[] = Object.keys(
      this.rawData.channels,
    ).map((ch, i) => ({
      x: sampledTime,
      y: this.downsample(this.rawData!.channels[ch], this.MAX_POINTS),
      name: ch,
      type: 'scattergl',
      mode: 'lines+markers',
      line: { color: this.getColor(i), width: 1 },
    }));

    const layout = this.getBaseLayout('Raw EEG Signals', isDark);
    const fn = isInit ? Plotly.newPlot : Plotly.react;
    fn('rawPlot', rawTraces, layout, this.getPlotConfig());
  }

  updateCleanedDataPlot(isInit = false, isDark: boolean = this.currentIsDark) {
    if (!this.cleanData) return;

    const sampledTime = this.downsample(this.cleanData.time, this.MAX_POINTS);

    const cleanTraces: Partial<Plotly.PlotData>[] = Object.keys(
      this.cleanData.channels,
    ).map((ch, i) => ({
      x: sampledTime,
      y: this.downsample(this.cleanData!.channels[ch], this.MAX_POINTS),
      name: ch,
      type: 'scattergl',
      mode: 'lines+markers',
      line: { color: this.getColor(i), width: 1 },
    }));

    const layout = this.getBaseLayout('Preprocessed Signals', isDark);
    const fn = isInit ? Plotly.newPlot : Plotly.react;
    fn('cleanPlot', cleanTraces, layout, this.getPlotConfig());
  }

  flattenForInitialPlot(subjects: EEGSubjectData[]): {
    time: number[];
    channels: EEGChannelData;
  } {
    const time: number[] = [];
    const channels: EEGChannelData = {};
    let currentOffset = 0;
    const GAP = 0.5;
    subjects.forEach((subject) => {
      subject.sessions.forEach((session) => {
        session.trials.forEach((trial) => {
          const shiftedTime = trial.time.map((t) => t + currentOffset);
          time.push(...shiftedTime);

          Object.entries(trial.channels).forEach(([ch, values]) => {
            if (!channels[ch]) {
              channels[ch] = [];
            }
            channels[ch].push(...values);
          });
          currentOffset += trial.time[trial.time.length - 1] + GAP;
        });
      });
    });

    return { time, channels };
  }

  // Spectrograms are usually pre-calculated matrices, so they are lighter,
  // but we still run them outside Angular to be safe.
  plotRawSpectrogram(
    channelIndex: number,
    isInit = false,
    isDark: boolean = this.currentIsDark,
  ) {
    const d = this.spectrogramDataRaw[channelIndex];
    if (!d) return;

    const zDb = d.values.map((row) =>
      row.map((v) => 10 * Math.log10(v + 1e-6)),
    );
    const layout = this.getBaseLayout(
      `Raw Spectrogram - ${this.availableChannels[channelIndex]}`,
      isDark,
    );
    layout.height = 400;
    layout.xaxis!.title = { text: 'Time (s)' };
    layout.yaxis!.title = { text: 'Frequency (Hz)' };

    const fn = isInit ? Plotly.newPlot : Plotly.react;
    fn(
      'rawSpectrogramPlot',
      [
        {
          x: d.times,
          y: d.frequencies,
          z: zDb,
          type: 'heatmap',
          colorscale: 'Jet',
          zsmooth: 'best',
          colorbar: {
            title: { text: 'dB' },
            tickfont: { color: layout.font!.color as string },
          },
        },
      ],
      layout,
      this.getPlotConfig(),
    );
  }

  plotCleanSpectrogram(
    channelIndex: number,
    isInit = false,
    isDark: boolean = this.currentIsDark,
  ) {
    const d = this.spectrogramDataClean[channelIndex];
    if (!d) return;

    const zDb = d.values.map((row) =>
      row.map((v) => 10 * Math.log10(v + 1e-6)),
    );
    const layout = this.getBaseLayout(
      `Clean Spectrogram - ${this.availableChannels[channelIndex]}`,
      isDark,
    );
    layout.height = 400;
    layout.xaxis!.title = { text: 'Time (s)' };
    layout.yaxis!.title = { text: 'Frequency (Hz)' };

    const fn = isInit ? Plotly.newPlot : Plotly.react;
    fn(
      'cleanSpectrogramPlot',
      [
        {
          x: d.times,
          y: d.frequencies,
          z: zDb,
          type: 'heatmap',
          colorscale: 'Jet',
          zsmooth: 'best',
          colorbar: {
            title: { text: 'dB' },
            tickfont: { color: layout.font!.color as string },
          },
        },
      ],
      layout,
      this.getPlotConfig(),
    );
  }

  getColor(idx: number): string {
    const hue = (idx * 137.508) % 360;
    return `hsl(${hue}, 70%, 50%)`;
  }

  handleNavbar(): void {
    this.workflowService.setNavState({
      '/upload': false,
      '/preprocess': false,
      '/analysis': false,
      '/visualization': false,
      '/algorithms': false,
    });
  }
  openAddPlotModal(): void {
    this.isAddPlotModalOpen = true;
  }
  closeAddPlotModal(): void {
    this.isAddPlotModalOpen = false;
  }
  createPlotFromSelection() {
    if (!this.canCreatePlot()) {
      this.errorMessage = 'Please select at least Subject, Session and Channel';
      return;
    }
    this.errorMessage = ``;
    this.closeAddPlotModal();
    this.loading = true;
    const sourceData =
      this.selectedDataType === 'clean' && this.cleanSubjects
        ? this.cleanSubjects
        : this.rawSubjects;

    const filteredSubjects: EEGSubjectData[] = this.applyFilter(sourceData);
    console.log('Filtered result:', filteredSubjects);

    const { traces, annotations, trialsMeta } =
      this.buildTracesWithGaps(filteredSubjects);
    if (traces.length === 0) {
      alert('No data matches your selection');
      return;
    }

    const id = 'plot_' + Date.now(); // unique

    const isDark = this.currentIsDark;

    const layout = this.getBaseLayout(
      `Subject ${this.selectedSubjectId} - Session ${this.selectedSessionId}`,
      isDark,
    );

    layout.xaxis = {
      ...layout.xaxis,
      title: { text: 'Time (s)' },
    };
    // layout.annotations = annotations;

    const plotFilters: PlotFilterRequest = {
      data_type: this.selectedDataType,
      subject_id: this.selectedSubjectId ?? '',
      session_id: this.selectedSessionId ?? '',
      labels: [...this.selectedLabels],
      categories: [...this.selectedCategories],
      channels: [...this.selectedChannels],
    };

    this.dynamicPlots.push({
      id,
      title: layout.title?.text ?? '',
      traces,
      layout,
      trialsMeta: trialsMeta,
      trialsCount: trialsMeta.length,
      filters: plotFilters,
    });

    setTimeout(() => {
      Plotly.newPlot(id, traces, layout, this.getPlotConfig());
      this.showPlotStatus(
        'Plot generated successfully. It is shown below.',
        'success',
      );
      this.scrollToPlot(id);
    }, 0);
    this.loading = false;
  }

  restoreSavedPlot(savedPlot: SavedPlotItem): void {
    const filters = savedPlot.filter_json;

    if (!filters) {
      console.error('Saved plot has no filter_json:', savedPlot);
      return;
    }

    this.selectedDataType = filters.data_type ?? 'raw';
    this.selectedSubjectId = Array.isArray(filters.subject)
      ? (filters.subject[0] ?? '')
      : (filters.subject ?? '');

    this.selectedSessionId = Array.isArray(filters.session)
      ? (filters.session[0] ?? '')
      : (filters.session ?? '');

    this.selectedLabels = [...(filters.labels ?? [])];
    this.selectedCategories = [...(filters.category ?? [])];
    this.selectedChannels = [...(filters.channels ?? [])];

    const sourceData =
      this.selectedDataType === 'clean' && this.cleanSubjects
        ? this.cleanSubjects
        : this.rawSubjects;

    if (!sourceData) return;

    const filteredSubjects = this.applyFilter(sourceData);
    const { traces, annotations, trialsMeta } =
      this.buildTracesWithGaps(filteredSubjects);

    if (traces.length === 0) {
      alert('No data matches this saved plot');
      return;
    }

    const id = 'plot_' + Date.now();
    const layout = this.getBaseLayout(savedPlot.plot_name, this.currentIsDark);

    layout.xaxis = {
      ...layout.xaxis,
      title: { text: 'Time (s)' },
    };

    this.dynamicPlots.push({
      id,
      title: savedPlot.plot_name,
      traces,
      layout,
      trialsMeta,
      trialsCount: trialsMeta.length,
      filters: {
        data_type: this.selectedDataType,
        subject_id: this.selectedSubjectId ?? '',
        session_id: this.selectedSessionId ?? '',
        labels: [...this.selectedLabels],
        categories: [...this.selectedCategories],
        channels: [...this.selectedChannels],
      },
    });

    setTimeout(() => {
      Plotly.newPlot(id, traces, layout, this.getPlotConfig());
      this.showPlotStatus(
        `Plot "${savedPlot.plot_name}" generated successfully. It is shown below.`,
        'success',
      );
      this.scrollToPlot(id);
    }, 0);
  }

  private applyFilter(sourceData: EEGSubjectData[]): EEGSubjectData[] {
    const filtered = sourceData
      // 1️⃣ Subjects
      .filter(
        (subject) =>
          this.selectedSubjectId?.length === 0 ||
          this.selectedSubjectId?.includes(subject.subjectId),
      )
      .map((subject) => ({
        subjectId: subject.subjectId,

        // 2️⃣ Sessions
        sessions: subject.sessions
          .filter(
            (session) =>
              this.selectedSessionId?.length === 0 ||
              this.selectedSessionId?.includes(session.sessionId),
          )
          .map((session) => ({
            sessionId: session.sessionId,

            // 3️⃣ Trials
            trials: session.trials
              .filter(
                (trial) =>
                  // label filter
                  (this.selectedLabels.length === 0 ||
                    this.selectedLabels.includes(trial.label)) &&
                  // category filter
                  (this.selectedCategories.length === 0 ||
                    this.selectedCategories.includes(trial.category ?? '')),
              )
              .map((trial) => ({
                trialId: trial.trialId,
                label: trial.label,
                category: trial.category,
                time: trial.time,

                // 4️⃣ Channels
                channels: this.filterChannels(trial.channels),
              }))
              // remove empty trials
              .filter((trial) => Object.keys(trial.channels).length > 0),
          }))
          // remove empty sessions
          .filter((session) => session.trials.length > 0),
      }))
      // remove empty subjects
      .filter((subject) => subject.sessions.length > 0);
    return filtered;
  }

  private buildTracesWithGaps(data: EEGSubjectData[]): {
    traces: Partial<Plotly.PlotData>[];
    annotations: any[];
    trialsMeta: TrialMeta[];
  } {
    const traces: Partial<Plotly.PlotData>[] = [];
    const annotations: any[] = [];
    const trialsMeta: TrialMeta[] = [];

    const GAP = 0.5; // half-second gap
    let timeOffset = 0;
    let trialCounter = 1;

    data.forEach((subject) => {
      subject.sessions.forEach((session) => {
        session.trials.forEach((trial) => {
          const startTime = timeOffset;
          const endTime = timeOffset + trial.time[trial.time.length - 1];

          trialsMeta.push({
            trialFileId: trial.trialId,
            trialPlotIndex: trialCounter++,
            subject: subject.subjectId,
            session: session.sessionId,
            label: trial.label,
            category: trial.category,
            start: startTime,
            end: endTime,
          });

          // // Plot title or annotation
          // annotations.push({
          //   x: timeOffset,
          //   y: 0,
          //   text: `Trial ${trial.trialId}`,
          //   showarrow: false,
          //   xanchor: 'left',
          //   font: { size: 12, color: '#000' },
          // });

          Object.keys(trial.channels).forEach((ch, idx) => {
            const shiftedTime = trial.time.map((t) => t + timeOffset);

            traces.push({
              x: shiftedTime,
              y: trial.channels[ch],
              type: 'scattergl',
              mode: 'lines+markers',
              name: `T${trialCounter - 1}-${ch}`,
              line: {
                color: this.getColor(idx + Math.random() * 1000),
                width: 1,
              },
            });
          });

          // Advance offset for next trial
          timeOffset += trial.time[trial.time.length - 1] + GAP;
        });
      });
    });

    return { traces, annotations, trialsMeta };
  }

  private filterChannels(channels: EEGChannelData): EEGChannelData {
    // if user didn’t select anything → keep all channels
    if (this.selectedChannels.length === 0) {
      return channels;
    }

    const filtered: EEGChannelData = {};

    for (const ch of this.selectedChannels) {
      if (channels[ch]) {
        filtered[ch] = channels[ch];
      }
    }

    return filtered;
  }

  getSubjects() {
    console.log(
      'Extracting subjects from raw data:',
      this.rawSubjects[0].sessions,
    );
    return this.rawSubjects.map((s) => s.subjectId);
  }

  getAllLabels(response: VisualizationResponse): string[] {
    const labels = new Set<string>();

    response.raw.forEach((subject) => {
      subject.sessions.forEach((session) => {
        session.trials.forEach((trial) => {
          labels.add(trial.label);
        });
      });
    });

    return Array.from(labels);
  }

  getAllCategories(response: VisualizationResponse): string[] {
    const categories = new Set<string>();

    response.raw.forEach((subject) => {
      subject.sessions.forEach((session) => {
        session.trials.forEach((trial) => {
          if (trial.category) {
            categories.add(trial.category);
          }
        });
      });
    });

    return Array.from(categories);
  }

  get activeSubjects(): EEGSubjectData[] {
    return this.selectedDataType === 'raw'
      ? this.rawSubjects
      : (this.cleanSubjects ?? []);
  }

  onSubjectChange(subjectId: string) {
    this.errorMessage = '';
    this.selectedSubjectId = subjectId;
    this.selectedSessionId = undefined;
    this.selectedTrials = [];
    this.selectedLabels = [];
    this.availableLabels = [];

    const subject = this.activeSubjects.find((s) => s.subjectId === subjectId);
    this.availableSessions = subject
      ? subject.sessions.map((s) => s.sessionId)
      : [];
    console.log('Selected subject:', subjectId);
    console.log(
      'Available sessions for subject',
      subjectId,
      ':',
      this.availableSessions,
    );
  }

  onSessionChange(sessionId: string) {
    this.errorMessage = '';
    this.selectedSessionId = sessionId;
    this.selectedTrials = [];

    const subject = this.activeSubjects.find(
      (s) => s.subjectId === this.selectedSubjectId,
    );

    const session = subject?.sessions.find((s) => s.sessionId === sessionId);
    this.availableTrials = session?.trials ?? [];

    const labels = new Set<string>();

    session?.trials.forEach((trial) => {
      if (trial.label && trial.label.trim() !== '') {
        labels.add(trial.label.trim());
      }
    });

    this.availableLabels = Array.from(labels);
    this.selectedLabels = [...this.availableLabels];
  }
  onChannelToggle(channel: string, event: Event) {
    this.errorMessage = '';
    const checked = (event.target as HTMLInputElement).checked;

    if (checked) {
      if (!this.selectedChannels.includes(channel)) {
        this.selectedChannels.push(channel);
      }
    } else {
      this.selectedChannels = this.selectedChannels.filter(
        (ch) => ch !== channel,
      );
    }
  }

  isAllChannelsSelected(): boolean {
    return this.selectedChannels.length === this.availableChannels.length;
  }

  onAllChannelsToggle(event: any) {
    if (event.target.checked) {
      this.selectedChannels = [...this.availableChannels];
    } else {
      this.selectedChannels = [];
    }
  }

  toggleLabel(label: string, event: Event) {
    const checked = (event.target as HTMLInputElement).checked;

    if (checked) {
      if (!this.selectedLabels.includes(label)) {
        this.selectedLabels.push(label);
      }
    } else {
      this.selectedLabels = this.selectedLabels.filter((l) => l !== label);
    }

    console.log('Selected Labels:', this.selectedLabels);
  }

  isAllLabelsSelected(): boolean {
    return (
      this.availableLabels.length > 0 &&
      this.selectedLabels.length === this.availableLabels.length
    );
  }

  onAllLabelsToggle(event: any) {
    if (event.target.checked) {
      this.selectedLabels = [...this.availableLabels];
    } else {
      this.selectedLabels = [];
    }
  }

  toggleCategory(category: string, event: Event) {
    const checked = (event.target as HTMLInputElement).checked;

    if (checked) {
      if (!this.selectedCategories.includes(category)) {
        this.selectedCategories.push(category);
      }
    } else {
      this.selectedCategories = this.selectedCategories.filter(
        (c) => c !== category,
      );
    }
    console.log('Selected Categories:', this.selectedCategories);
  }

  canCreatePlot(): boolean {
    return (
      this.selectedSubjectId != undefined &&
      this.selectedSessionId != undefined &&
      this.selectedChannels.length > 0
    );
  }
  removePlot(id: string) {
    Plotly.purge(id);
    this.dynamicPlots = this.dynamicPlots.filter((p) => p.id !== id);
  }

  openSaveModal(plot: any) {
    this.selectedPlotToSave = plot;
    this.savePlotName = plot.title || '';
    this.isSaveModalOpen = true;
  }

  closeSaveModal() {
    this.isSaveModalOpen = false;
    this.savePlotName = '';
    this.selectedPlotToSave = null;
  }

  savePlot() {
    const configId = this.workflowService.getConfiguredFileId();
    console.log(configId);

    if (!configId || !this.selectedPlotToSave || !this.savePlotName.trim())
      return;

    const payload: SavePlotRequest = {
      config_id: configId,
      plot_name: this.savePlotName.trim(),
      filters: this.selectedPlotToSave.filters,
    };

    this.visualizationService.savePlot(payload).subscribe({
      next: (res) => {
        this.selectedPlotToSave.title = this.savePlotName.trim();
        this.loadSavedPlots(payload.config_id);
        this.closeSaveModal();
        this.showPlotStatus(
          `"${payload.plot_name}" has been saved to your history.`,
          'success',
        );
      },
      error: (err) => {
        console.error(err);
        this.showPlotStatus('Failed to save plot. Please try again.', 'error');
      },
    });
  }

  openHistoryPanel(): void {
    this.showHistoryPanel = true;
  }

  closeHistoryPanel(): void {
    this.showHistoryPanel = false;
  }

  onHistoryGenerate(plot: any): void {
    this.restoreSavedPlot(plot);
  }

  onHistoryDelete(plot: SavedPlotItem): void {
    const plotId = Number(plot.plot_id);
    if (Number.isNaN(plotId)) return;

    const previousItems = [...this.historyItems];
    this.historyItems = this.historyItems.filter(
      (p) => Number(p.plot_id) !== plotId,
    );

    this.visualizationService.deletePlot(plotId).subscribe({
      next: () => {},
      error: (err) => {
        console.error('Failed to delete plot', err);
        this.historyItems = previousItems;
        this.errorMessage = 'Failed to delete plot';
      },
    });
  }

  onHistoryDeleteAll(): void {
    const configId = this.workflowService.getConfiguredFileId();
    if (!configId) return;

    const previous = [...this.historyItems];
    this.historyItems = [];

    this.visualizationService.deleteAllPlots(configId).subscribe({
      error: (err) => {
        console.error('Failed to delete all plots', err);
        this.historyItems = previous;
      },
    });
  }

  private normalizeFilters(filters: any) {
    const parsed = typeof filters === 'string' ? JSON.parse(filters) : filters;

    return {
      data_type: parsed?.data_type ?? 'raw',
      subject: parsed?.subject_id ?? parsed?.subject ?? '',
      session: parsed?.session_id ?? parsed?.session ?? '',
      labels: parsed?.labels ?? [],
      category: parsed?.categories ?? parsed?.category ?? [],
      channels: parsed?.channels ?? [],
      montage: parsed?.montage ?? 'standard_1020',
    };
  }

  private showPlotStatus(
    message: string,
    type: 'success' | 'error' | 'info' = 'success',
  ): void {
    this.plotStatusMessage = message;
    this.plotStatusType = type;

    if (this.plotStatusTimer) {
      clearTimeout(this.plotStatusTimer);
    }

    this.plotStatusTimer = setTimeout(() => {
      this.plotStatusMessage = '';
    }, 3500);
  }

  clearPlotStatus(): void {
    this.plotStatusMessage = '';
    if (this.plotStatusTimer) {
      clearTimeout(this.plotStatusTimer);
      this.plotStatusTimer = null;
    }
  }
  private scrollToPlot(plotId: string): void {
    setTimeout(() => {
      const el = document.getElementById(plotId);
      if (el) {
        el.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    }, 100);
  }
}
