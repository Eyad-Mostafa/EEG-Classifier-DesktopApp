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

export interface AiTutorialStep {
  selector: string | null;
  icon: string;
  title: string;
  description: string;
  badge?: string;
  cardPosition: 'center' | 'left';
  showGhostBar: boolean;
  // Which edge of the TARGET to attach the line to
  targetAnchor: 'top' | 'bottom' | 'left' | 'none';
  // Which edge of the CARD to attach the line to
  cardAnchor: 'top' | 'bottom' | 'right';
}

interface LineCoords {
  // Start point (dot goes here)
  x1: number; y1: number;
  // End point (arrowhead goes here)
  x2: number; y2: number;
  // SVG path
  d: string;
}

interface HighlightRect {
  top: number; left: number; width: number; height: number;
}

@Component({
  selector: 'app-ai-models-tutorial',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './ai-models-tutorial.component.html',
})
export class AiModelsTutorialComponent implements AfterViewInit, OnDestroy {
  @Output() closed = new EventEmitter<void>();
  @Output() ghostBarActive = new EventEmitter<boolean>();

  currentStep = 0;
  lineCoords: LineCoords | null = null;
  highlightRect: HighlightRect | null = null;
  showGhostBar = false;

  private resizeObserver?: ResizeObserver;
  private recalcTimeout?: ReturnType<typeof setTimeout>;

  readonly steps: AiTutorialStep[] = [
  {
    selector: null,
    icon: 'model_training',
    title: 'AI Classification',
    description: 'Select a trained neural network model, then run prediction to classify every trial in your configured EEG data — identifying each as motor execution or motor imagery.',
    cardPosition: 'center',
    showGhostBar: false,
    targetAnchor: 'none',
    cardAnchor: 'top',
  },
  {
    selector: '[data-ai-section="models-grid"]',
    icon: 'memory',
    title: 'Choose a model',
    description: 'Each card shows a trained architecture with its input requirements, accuracy, and preprocessing steps it expects. Click a card to select it, then click the architecture image to inspect it in detail.',
    cardPosition: 'left',
    showGhostBar: false,
    targetAnchor: 'top',
    cardAnchor: 'right',
  },
  {
    selector: '[data-ai-tutorial="ghost-maplabels"]',
    icon: 'compare_arrows',
    title: 'Map labels for ground-truth metrics',
    description:
    'If your file has known labels, map them to the model\'s output classes. The app will then compute real accuracy, F1, precision, and recall — a verified measure of model performance on your data.',
    cardPosition: 'center',
    showGhostBar: true,
    targetAnchor: 'top',
    cardAnchor: 'bottom',
  },
  {
    selector: '[data-ai-tutorial="ghost-autopreprocess"]',
    icon: 'auto_fix_high',
    title: 'Auto-Preprocess',
    description: 'After selecting a model, a bar appears at the bottom. Toggle Auto-Preprocess to apply the model\'s required pipeline automatically before inference — no manual setup needed.',
    cardPosition: 'center',
    showGhostBar: true,
    targetAnchor: 'top',
    cardAnchor: 'bottom',
  },
  {
    selector: '[data-ai-tutorial="ghost-runbtn"]',
    icon: 'play_circle',
    title: 'Run Prediction',
    description: 'Hit Run Prediction to start inference. The model processes every trial in your current data configuration and returns a predicted class with a confidence score per trial.',
    cardPosition: 'center',
    showGhostBar: true,
    targetAnchor: 'top',
    cardAnchor: 'bottom',
  },
  {
    selector: null,
    icon: 'download',
    title: 'Export results',
    description:
      'After running a prediction, export the full results table as a CSV file — ready for reporting, sharing with supervisors, or further analysis in external tools.',
    cardPosition: 'center',
    showGhostBar: false,
    targetAnchor: 'none',
    cardAnchor: 'top',
  },
];

  constructor(private cdr: ChangeDetectorRef, private zone: NgZone) {}

  get step(): AiTutorialStep { return this.steps[this.currentStep]; }
  get isFirst(): boolean { return this.currentStep === 0; }
  get isLast(): boolean { return this.currentStep === this.steps.length - 1; }
  get cardLeft(): boolean { return this.step.cardPosition === 'left'; }

  ngAfterViewInit(): void {
    this.resizeObserver = new ResizeObserver(() => {
      this.zone.run(() => this.scheduleRecalc(100));
    });
    this.resizeObserver.observe(document.body);
    // First render — no animations to wait for
    this.applyStep(200);
  }

  ngOnDestroy(): void {
    this.resizeObserver?.disconnect();
    clearTimeout(this.recalcTimeout);
  }

  next(): void {
    if (!this.isLast) { this.currentStep++; this.applyStep(); }
    else { this.close(); }
  }

  prev(): void {
    if (!this.isFirst) { this.currentStep--; this.applyStep(); }
  }

  goTo(i: number): void {
    this.currentStep = i;
    this.applyStep();
  }

  close(): void {
    this.ghostBarActive.emit(false);
    this.closed.emit();
  }

  onBackdropClick(event: MouseEvent): void {
    if ((event.target as HTMLElement).classList.contains('ai-tutorial-backdrop')) {
      this.close();
    }
  }

  private applyStep(delay = 330): void {
    // Clear any pending line — avoids stale lines showing during transition
    this.lineCoords = null;
    this.highlightRect = null;

    // Update ghost bar state immediately so it's in the DOM
    const needsGhost = this.step.showGhostBar;
    if (this.showGhostBar !== needsGhost) {
      this.showGhostBar = needsGhost;
      this.ghostBarActive.emit(needsGhost);
    }

    this.cdr.detectChanges();

    // Schedule the measurement after all CSS transitions finish:
    // - Card position change (left↔center): 500ms transition
    // - Card lift (-translate-y-16): 500ms transition
    // - Ghost bar slide-in: 300ms
    // We wait for the longest one plus a small buffer
    this.scheduleRecalc(delay);
  }

  private scheduleRecalc(delay: number): void {
    clearTimeout(this.recalcTimeout);
    this.recalcTimeout = setTimeout(() => this.recalc(), delay);
  }

  private recalc(): void {
    this.lineCoords = null;
    this.highlightRect = null;

    const sel = this.step.selector;
    if (!sel || this.step.targetAnchor === 'none') {
      this.cdr.detectChanges();
      return;
    }

    const targetEl = document.querySelector(sel) as HTMLElement | null;
    const cardEl   = document.querySelector('.ai-tutorial-card') as HTMLElement | null;
    if (!targetEl || !cardEl) { this.cdr.detectChanges(); return; }

    const t = targetEl.getBoundingClientRect();
    const c = cardEl.getBoundingClientRect();

    this.highlightRect = {
      top:    t.top    - 6,
      left:   t.left   - 8,
      width:  t.width  + 16,
      height: t.height + 12,
    };

    // --- Card exit point (dot origin) ---
    let cx: number, cy: number;
    switch (this.step.cardAnchor) {
      case 'bottom':
        cx = c.left + c.width / 2;
        cy = c.bottom + 6;
        break;
      case 'right':
        cx = c.right + 6;
        cy = c.top + c.height / 2;
        break;
      default: // 'top'
        cx = c.left + c.width / 2;
        cy = c.top - 6;
        break;
    }

    // --- Target entry point (arrowhead destination) ---
    let tx: number, ty: number;
    switch (this.step.targetAnchor) {
      case 'left':
        tx = t.left - 6;
        ty = t.top + t.height / 2;
        break;
      default: // 'top'
        tx = t.left + t.width / 2;
        ty = t.top - 6;
        break;
    }

    // Dot at card (x1,y1), arrowhead at target (x2,y2)
    const x1 = cx, y1 = cy;
    const x2 = tx, y2 = ty;

    // Control points for the bezier — midpoint between the two anchors
    const mx = (x1 + x2) / 2;
    const my = (y1 + y2) / 2;

    // For horizontal lines (card right → target left): curve gently
    // For vertical lines (card bottom → target top): curve through midpoint
    let d: string;
    if (this.step.cardAnchor === 'right') {
      // Horizontal bezier: control points keep x-axis curve
      d = `M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`;
    } else {
      // Vertical bezier: control points keep y-axis curve
      d = `M ${x1} ${y1} C ${x1} ${my}, ${x2} ${my}, ${x2} ${y2}`;
    }

    this.lineCoords = { x1, y1, x2, y2, d };
    this.cdr.detectChanges();
  }
}