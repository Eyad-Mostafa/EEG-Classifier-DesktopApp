import { Injectable } from '@angular/core';
import { BehaviorSubject, Observable, of } from 'rxjs';
import {
    FileHistory,
    UserHistory,
    FileHistoryDetail,
    FileConfiguration
} from '../models/history.model';

@Injectable({
    providedIn: 'root'
})
export class HistoryService {
    private historySubject = new BehaviorSubject<UserHistory>(this.getMockHistory());
    history$ = this.historySubject.asObservable();

    private selectedFileIdSubject = new BehaviorSubject<string | null>(null);
    selectedFileId$ = this.selectedFileIdSubject.asObservable();

    constructor() { }

    getHistory(): Observable<UserHistory> {
        return of(this.historySubject.value);
    }

    getFileDetails(fileId: string): FileHistoryDetail | undefined {
        return this.historySubject.value.details.get(fileId);
    }

    selectFile(fileId: string): void {
        this.selectedFileIdSubject.next(fileId);
    }

    clearSelection(): void {
        this.selectedFileIdSubject.next(null);
    }

    private getMockHistory(): UserHistory {
        const details = new Map<string, FileHistoryDetail>();

        // File 1 details with configuration
        details.set('1', {
            fileId: '1',
            fileName: 'subject_01_eeg.csv',
            samplingRate: 500,
            preprocessing: [
                { name: 'Bandpass Filter', parameters: { lowcut: 1, highcut: 45 }, order: 1 },
                { name: 'Notch Filter', parameters: { frequency: 50 }, order: 2 },
                { name: 'ICA', parameters: { components: 20 }, order: 3 }
            ],
            analyses: [
                { type: 'spectral', name: 'Power Spectral Density', parameters: { method: 'welch', window: 'hann' } },
                { type: 'connectivity', name: 'Functional Connectivity', parameters: { method: 'coh', bands: ['alpha', 'beta'] } }
            ],
            visualizations: [
                { type: 'time_series', title: 'Raw EEG Signals', config: { channels: [0, 1, 2], timeRange: [0, 10] } },
                { type: 'spectrogram', title: 'Time-Frequency Analysis', config: { channel: 0, freqRange: [1, 45] } }
            ],
            // NEW: Add configuration
            configuration: {
                labels: {
                    '0': 'motor',
                    '1': 'imagery',
                    '2': 'rest'
                },
                channelMapping: {
                    'channel_1': 'Fp1',
                    'channel_2': 'Fz',
                    'channel_3': 'Cz',
                    'channel_4': 'Pz',
                    'channel_5': 'Oz',
                    'channel_6': 'F3',
                    'channel_7': 'F4',
                    'channel_8': 'C3',
                    'channel_9': 'C4',
                    'channel_10': 'P3',
                    'channel_11': 'P4',
                    'channel_12': 'O1',
                    'channel_13': 'O2'
                },
                selectedMontage: 'standard_1020',
                selectedSubjects: [
                    { subjectId: '1', sessions: ['1', '2', '3'] },
                    { subjectId: '2', sessions: ['1', '2'] }
                ],
                totalSubjectsSelected: 2,
                totalSessionsSelected: 5
            }
        });

        // File 2 details with configuration
        details.set('2', {
            fileId: '2',
            fileName: 'subject_02_eeg.csv',
            samplingRate: 1000,
            preprocessing: [
                { name: 'Bandpass Filter', parameters: { lowcut: 0.5, highcut: 40 }, order: 1 },
                { name: 'CAR', parameters: { type: 'common_average' }, order: 2 },
                { name: 'Epoch Rejection', parameters: { threshold: 100, method: 'amplitude' }, order: 3 }
            ],
            analyses: [
                { type: 'csp', name: 'Common Spatial Patterns', parameters: { components: 6 } },
                { type: 'entropy', name: 'Differential Entropy', parameters: { bands: ['delta', 'theta', 'alpha', 'beta', 'gamma'] } }
            ],
            visualizations: [
                { type: 'time_series', title: 'Preprocessed EEG', config: { channels: 'all', showEvents: true } },
                { type: 'connectivity', title: 'Connectivity Matrix', config: { threshold: 0.6, layout: 'circular' } }
            ],
            // NEW: Add configuration
            configuration: {
                labels: {
                    '0': 'left_hand',
                    '1': 'right_hand',
                    '2': 'feet',
                    '3': 'tongue'
                },
                channelMapping: {
                    'channel_1': 'Fp1',
                    'channel_2': 'Fp2',
                    'channel_3': 'F3',
                    'channel_4': 'F4',
                    'channel_5': 'C3',
                    'channel_6': 'C4',
                    'channel_7': 'P3',
                    'channel_8': 'P4',
                    'channel_9': 'O1',
                    'channel_10': 'O2'
                },
                selectedMontage: 'biosemi32',
                selectedSubjects: [
                    { subjectId: '1', sessions: ['1', '2', '3', '4'] },
                    { subjectId: '2', sessions: ['1', '2', '3'] },
                    { subjectId: '3', sessions: ['1', '2'] }
                ],
                totalSubjectsSelected: 3,
                totalSessionsSelected: 9
            }
        });

        // File 3 details with configuration
        details.set('3', {
            fileId: '3',
            fileName: 'resting_state.csv',
            samplingRate: 250,
            preprocessing: [
                { name: 'Bandpass Filter', parameters: { lowcut: 0.1, highcut: 30 }, order: 1 },
                { name: 'Baseline Correction', parameters: { window: [-200, 0] }, order: 2 },
                { name: 'ICA', parameters: { components: 15, method: 'fastica' }, order: 3 }
            ],
            analyses: [
                { type: 'microstate', name: 'Microstate Analysis', parameters: { n_states: 4, method: 'kmeans' } },
                { type: 'pac', name: 'Phase-Amplitude Coupling', parameters: { phaseFreq: [4, 8], ampFreq: [30, 50] } }
            ],
            visualizations: [
                { type: 'ica', title: 'ICA Components', config: { nComponents: 10, showTopo: true } },
                { type: 'topomap', title: 'Microstate Maps', config: { microstates: [1, 2, 3, 4] } }
            ],
            // NEW: Add configuration
            configuration: {
                labels: {
                    '0': 'eyes_open',
                    '1': 'eyes_closed'
                },
                channelMapping: {
                    'channel_1': 'Fp1',
                    'channel_2': 'Fp2',
                    'channel_3': 'F7',
                    'channel_4': 'F3',
                    'channel_5': 'Fz',
                    'channel_6': 'F4',
                    'channel_7': 'F8',
                    'channel_8': 'T7',
                    'channel_9': 'C3',
                    'channel_10': 'Cz',
                    'channel_11': 'C4',
                    'channel_12': 'T8',
                    'channel_13': 'P7',
                    'channel_14': 'P3',
                    'channel_15': 'Pz',
                    'channel_16': 'P4',
                    'channel_17': 'P8',
                    'channel_18': 'O1',
                    'channel_19': 'Oz',
                    'channel_20': 'O2'
                },
                selectedMontage: 'standard_1005',
                selectedSubjects: [
                    { subjectId: '1', sessions: ['1', '2', '3'] }
                ],
                totalSubjectsSelected: 1,
                totalSessionsSelected: 3
            }
        });

        return {
            files: [
                {
                    id: '1',
                    fileName: 'subject_01_eeg.csv',
                    uploadDate: new Date('2026-02-25T10:30:00'),
                    samplingRate: 500,
                    duration: 120,
                    channels: 32,
                    fileSize: '45.2 MB',
                    fileType: 'csv'
                },
                {
                    id: '2',
                    fileName: 'subject_02_eeg.csv',
                    uploadDate: new Date('2026-02-24T15:45:00'),
                    samplingRate: 1000,
                    duration: 180,
                    channels: 64,
                    fileSize: '128.5 MB',
                    fileType: 'csv'
                },
                {
                    id: '3',
                    fileName: 'resting_state.csv',
                    uploadDate: new Date('2026-02-23T09:15:00'),
                    samplingRate: 250,
                    duration: 300,
                    channels: 19,
                    fileSize: '78.1 MB',
                    fileType: 'csv'
                }
            ],
            details: details
        };
    }
}