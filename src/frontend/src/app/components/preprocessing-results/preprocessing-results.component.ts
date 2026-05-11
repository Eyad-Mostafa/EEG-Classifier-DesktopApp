import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { WorkflowService } from '../../services/workflow.service';
import { PreprocessingService } from '../../services/preprocessing.service';
import { AlgorithmStep } from '../../models/api/preprocessing.model.api';

type DownloadState = 'idle' | 'downloading' | 'done' | 'error';

@Component({
  selector: 'app-preprocessing-results',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './preprocessing-results.component.html',
  styleUrls: ['./preprocessing-results.component.css'],
})
export class PreprocessingResultsComponent implements OnInit {
  preprocessingConfig: AlgorithmStep[] | null = null;
  figureOriginalData: string | null = null;
  figureProcessedData: string | null = null;
  private zoomScale = 1;
  
  // Download state
  downloadState: DownloadState = 'idle';
  downloadProgress = 0; // 0-100, for the progress bar
  
  // Image zoom
  zoomedImage: string | null = null; // base64 src of the zoomed image
  zoomedLabel: string | null = null;
  
  stats = [
    { icon: 'analytics', label: 'Algorithms Applied', value: '0' },
    { icon: 'timer', label: 'Processing Time', value: '0 s' },
    { icon: 'description', label: 'Output Size', value: '0 MB' },
  ];
  
  constructor(
    private router: Router,
    private workflowService: WorkflowService,
    private preprocessingService: PreprocessingService
  ) {}
  
  ngOnInit(): void {
    this.preprocessingConfig =
    this.workflowService.getPreprocessingConfig() as AlgorithmStep[];

    if (this.preprocessingConfig) {
      this.stats[0].value = this.preprocessingConfig.length.toString();
    }

    const fileSize = this.workflowService.getResultFileSize();
    if (fileSize) this.stats[2].value = fileSize;
    
    const processingTime = this.workflowService.getProcessingTime();
    if (processingTime) this.stats[1].value = processingTime + 's';

    this.figureOriginalData = this.workflowService.getFigureOriginalData();
    this.figureProcessedData = this.workflowService.getFigureProcessedData();

    this.updateResultFileName();
    this.handleNavbar();
  }

  // ── Download — non-blocking ──────────────────────────────────────────────

  handleDownload(): void {
    if (this.downloadState === 'downloading') return;

    const fileId = this.workflowService.getResultFileId();
    if (!fileId) return;

    let originalName = this.workflowService.getUploadedFileName() || 'recording';
    originalName = originalName.replace('.csv', '');
    const finalFilename = `preprocessed-${originalName}.csv`;

    this.downloadState = 'downloading';
    this.downloadProgress = 0;

    // Fake progress so the user sees movement immediately
    const progressInterval = setInterval(() => {
      if (this.downloadProgress < 85) this.downloadProgress += 5;
    }, 120);

    this.preprocessingService.downloadResult(fileId).subscribe({
      next: (response) => {
        clearInterval(progressInterval);
        this.downloadProgress = 100;

        const blob = new Blob([response.body!], { type: 'text/csv' });
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = finalFilename;
        a.click();
        window.URL.revokeObjectURL(url);

        this.downloadState = 'done';
        // Reset after 3s so user can download again
        setTimeout(() => {
          this.downloadState = 'idle';
          this.downloadProgress = 0;
        }, 3000);
      },
      error: (err) => {
        clearInterval(progressInterval);
        console.error('Download error:', err);
        this.downloadState = 'error';
        setTimeout(() => {
          this.downloadState = 'idle';
          this.downloadProgress = 0;
        }, 3000);
      },
    });
  }

  get downloadLabel(): string {
    switch (this.downloadState) {
      case 'downloading': return 'Downloading...';
      case 'done': return 'Saved!';
      case 'error': return 'Failed — retry';
      default: return 'Download CSV';
    }
  }

  get downloadIcon(): string {
    switch (this.downloadState) {
      case 'downloading': return 'hourglass_top';
      case 'done': return 'check_circle';
      case 'error': return 'error_outline';
      default: return 'download';
    }
  }

  // ── Image zoom ───────────────────────────────────────────────────────────

  openZoom(base64: string | null, label: string): void {
    if (!base64) return;
    this.zoomedImage = 'data:image/png;base64,' + base64;
    this.zoomedLabel = label;
  }

  closeZoom(): void {
    this.zoomedImage = null;
    this.zoomedLabel = null;
  }

  // ── Navigation ───────────────────────────────────────────────────────────

  handleBack(): void {
    this.router.navigate(['/preprocess']);
  }

  handleContinue(): void {
    this.router.navigate(['/analysis']);
  }

  updateResultFileName(): void {
    let originalName = this.workflowService.getUploadedFileName() || 'recording';
    originalName = originalName.replace('.csv', '');
    this.workflowService.setResultFileName(`preprocessed-${originalName}.csv`);
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


  onZoomWheel(event: WheelEvent): void {
    event.preventDefault();
    const img = event.currentTarget as HTMLImageElement;
    const delta = event.deltaY > 0 ? -0.1 : 0.1;
    this.zoomScale = Math.min(5, Math.max(0.5, this.zoomScale + delta));
    img.style.transform = `scale(${this.zoomScale})`;
  }

}