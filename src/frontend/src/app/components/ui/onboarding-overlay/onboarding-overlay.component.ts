import {
  Component,
  EventEmitter,
  Output,
  AfterViewInit,
  OnDestroy,
  ChangeDetectorRef,
  NgZone,
} from '@angular/core';
import { CommonModule } from '@angular/common';

export interface OnboardingStep {
  navSelector: string | null;
  icon: string;
  title: string;
  description: string;
  tip?: string;
  pageLabel: string | null;
}

interface LineCoords {
  d: string;
  x1: number;
  y1: number;
}

interface HighlightRect {
  top: number;
  left: number;
  width: number;
  height: number;
}

@Component({
  selector: 'app-onboarding-overlay',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './onboarding-overlay.component.html',
})
export class OnboardingOverlayComponent implements AfterViewInit, OnDestroy {
  @Output() closed = new EventEmitter<void>();

  currentStep = 0;
  lineCoords: LineCoords | null = null;
  highlightRect: HighlightRect | null = null;

  private resizeObserver?: ResizeObserver;

  readonly steps: OnboardingStep[] = [
    {
      navSelector: null,
      icon: 'hub',
      title: 'Welcome to EEGClassifier',
      description:
        'A complete platform for EEG signal preprocessing, analysis, visualization, and AI-powered motor imagery classification.',
      tip: 'For the best experience, avoid moving or renaming your EEG files after using them. The app tracks file paths across sessions, and altering them will disconnect your history.',
      pageLabel: null,
    },
    {
      navSelector: '[data-nav="choose"]',
      icon: 'folder_open',
      title: 'Choose your EEG file',
      description:
        'Choose a CSV file and set your sampling rate. Previously processed files appear in the History panel on the right — click any entry to reload it instantly without re-choosing.',
      pageLabel: 'File browsing page',
    },
    {
      navSelector: '[data-nav="config"]',
      icon: 'tune',
      title: 'Configure your data subset',
      description:
        'Filter by specific subjects, sessions, and trials. Each configuration is saved automatically. From here you can skip directly to Analysis or AI Classification — preprocessing is optional.',
      pageLabel: 'Config page',
    },
    {
      navSelector: '[data-nav="preprocess"]',
      icon: 'science',
      title: 'Build a preprocessing pipeline',
      description:
        'Drag and drop signal processing methods, configure their parameters, and save pipelines for reuse. The Results tab lets you inspect and download the processed file.',
      pageLabel: 'Preprocessing page',
    },
    {
      navSelector: '[data-nav="analysis"]',
      icon: 'analytics',
      title: 'Run analysis methods',
      description:
        'Apply statistical and spectral analysis to raw or preprocessed data. Results are cached automatically — switch between files without re-running everything.',
      pageLabel: 'Analysis page',
    },
    {
      navSelector: '[data-nav="viz"]',
      icon: 'visibility',
      title: 'Visualize your signals',
      description:
        'Explore multiple visualization modes to understand your EEG data before and after preprocessing — useful for spotting artifacts and validating your pipeline.',
      pageLabel: 'Visualization page',
    },
    {
      navSelector: '[data-nav="ai"]',
      icon: 'model_training',
      title: 'AI classification',
      description:
        'Use pretrained models to classify each EEG trial — motor execution or motor imagery. Predictions run per-trial on your currently configured data.',
      pageLabel: 'AI Models page',
    },
    {
      navSelector: '[data-nav="algorithms"]',
      icon: 'library_books',
      title: 'Explore algorithms',
      description:
        'The Algorithms page documents every available method — descriptions, parameters, and use cases. A useful reference while building your preprocessing pipeline.',
      pageLabel: 'Algorithms page',
    },
  ];

  constructor(private cdr: ChangeDetectorRef, private zone: NgZone) {}

  get step(): OnboardingStep {
    return this.steps[this.currentStep];
  }

  get isFirst(): boolean {
    return this.currentStep === 0;
  }

  get isLast(): boolean {
    return this.currentStep === this.steps.length - 1;
  }

  ngAfterViewInit(): void {
    // Enable all nav items visually during onboarding
    document.querySelector('header')?.classList.add('onboarding-active');

    this.resizeObserver = new ResizeObserver(() => {
      this.zone.run(() => this.recalc());
    });
    this.resizeObserver.observe(document.body);
    setTimeout(() => this.recalc(), 200);
  }

  ngOnDestroy(): void {
    // Restore normal nav state when onboarding closes
    document.querySelector('header')?.classList.remove('onboarding-active');
    this.resizeObserver?.disconnect();
  }

  next(): void {
    if (this.isLast) { this.close(); return; }
    this.currentStep++;
    setTimeout(() => this.recalc(), 50);
  }

  prev(): void {
    if (!this.isFirst) {
      this.currentStep--;
      setTimeout(() => this.recalc(), 50);
    }
  }

  goTo(i: number): void {
    this.currentStep = i;
    setTimeout(() => this.recalc(), 50);
  }

  close(): void {
    this.closed.emit();
  }

  onBackdropClick(event: MouseEvent): void {
    if ((event.target as HTMLElement).classList.contains('onboarding-backdrop')) {
      this.close();
    }
  }

  private recalc(): void {
    this.lineCoords = null;
    this.highlightRect = null;

    const sel = this.step.navSelector;
    if (!sel) { this.cdr.detectChanges(); return; }

    const navEl  = document.querySelector(sel) as HTMLElement | null;
    const cardEl = document.querySelector('.onboarding-card') as HTMLElement | null;
    if (!navEl || !cardEl) { this.cdr.detectChanges(); return; }

    const nRect = navEl.getBoundingClientRect();
    const cRect = cardEl.getBoundingClientRect();

    // Highlight ring around the nav item
    this.highlightRect = {
      top:    nRect.top    - 4,
      left:   nRect.left   - 6,
      width:  nRect.width  + 12,
      height: nRect.height + 8,
    };

    // Dot at card TOP center (origin — where the explanation comes from)
    const x1 = cRect.left + cRect.width / 2;
    const y1 = cRect.top - 6;

    // Arrowhead at nav BOTTOM center (destination — what is being pointed at)
    const x2 = nRect.left + nRect.width / 2;
    const y2 = nRect.bottom + 4;

    // Bezier control point — midpoint creates a smooth upward curve
    const my = y1 + (y2 - y1) * 0.45;

    this.lineCoords = {
      x1, y1,
      d: `M ${x1} ${y1} C ${x1} ${my}, ${x2} ${my}, ${x2} ${y2}`,
    };

    this.cdr.detectChanges();
  }
}