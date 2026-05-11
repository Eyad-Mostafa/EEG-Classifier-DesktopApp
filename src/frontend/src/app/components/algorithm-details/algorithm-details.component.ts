import { Component, EventEmitter, Input, Output, OnChanges, SimpleChanges } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AlgorithmService } from '../../services/algorithm.service';
import { AlgorithmInfo } from '../../models/api/algorithm-library.model.api';
import { AppLoaderComponent } from '../ui/app-loader/app-loader.component';

// Define the Electron API interface for TypeScript
declare global {
  interface Window {
    electronAPI?: {
      openPdf: (filename: string, displayName: string) => Promise<void>;
    };
  }
}

@Component({
  selector: 'app-algorithm-details',
  standalone: true,
  imports: [CommonModule, AppLoaderComponent],
  templateUrl: './algorithm-details.component.html',
  styleUrls: [] 
})
export class AlgorithmDetailsComponent implements OnChanges {
  @Input() type: 'preprocessing' | 'analysis' = 'preprocessing';
  @Input() algorithmId: string | null | undefined = null;
  @Output() close = new EventEmitter<void>();

  fullAlgorithmDetails: AlgorithmInfo | null = null;
  isLoading = false;
  errorMessage = '';

  constructor(private algorithmService: AlgorithmService) {}

  ngOnChanges(changes: SimpleChanges): void {
    if (changes['algorithmId'] && this.algorithmId) {
      this.fetchFullDetails(this.algorithmId);
    }
  }

  openManual(): void {

    if (!this.algorithmId || !this.fullAlgorithmDetails) {
      console.warn('Cannot open manual: Algorithm details not loaded yet.');
      return;
    }

    const sourceFilename = `${this.algorithmId}.pdf`;

    const cleanName = this.fullAlgorithmDetails.name.replace(/\s+/g, '_') + '_Manual.pdf';

    if (window.electronAPI) {
      window.electronAPI.openPdf(sourceFilename, cleanName)
        .catch(err => console.error('Failed to open PDF via Electron:', err));
    } else {
      window.open(`assets/algorithms-docs/${sourceFilename}`, '_blank');
    }
  }

  private fetchFullDetails(id: string): void {
    this.isLoading = true;
    this.errorMessage = '';
    this.fullAlgorithmDetails = null;

    this.algorithmService.getAlgorithmById(id, this.type).subscribe({
      next: (data) => {
        this.fullAlgorithmDetails = data;
        this.isLoading = false;
      },
      error: (err) => {
        console.error('Failed to load details', err);
        this.errorMessage = 'Could not load algorithm details.';
        this.isLoading = false;
      }
    });
  }
}