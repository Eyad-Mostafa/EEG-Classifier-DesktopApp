import {
  Component,
  EventEmitter,
  Output,
  ViewChild,
  ElementRef,
  AfterViewInit,
  OnDestroy,
  ChangeDetectorRef,
} from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-tutorial-overlay',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './tutorial-overlay.component.html',
  styleUrls: [],
})
export class TutorialOverlayComponent implements AfterViewInit, OnDestroy {
  @Output() closed = new EventEmitter<void>();
  @ViewChild('videoPlayer') videoPlayer!: ElementRef<HTMLVideoElement>;

  currentVideoSrc = '';
  private observer?: MutationObserver;

  constructor(private cdr: ChangeDetectorRef) { }

  ngAfterViewInit(): void {
    const updateVideo = () => {
      const isDark = document.documentElement.classList.contains('dark');
      const nextSrc = isDark
        ? 'assets/videos/preprocessing-dark.mp4'
        : 'assets/videos/preprocessing-light.mp4';

      if (this.currentVideoSrc === nextSrc) return;

      this.currentVideoSrc = nextSrc;
      this.cdr.detectChanges();

      setTimeout(() => {
        const v = this.videoPlayer?.nativeElement;
        if (!v) return;
        v.pause();
        v.load();
        v.play().catch(() => { });
      }, 0);
    };

    updateVideo();

    this.observer = new MutationObserver(() => updateVideo());
    this.observer.observe(document.documentElement, {
      attributes: true,
      attributeFilter: ['class'],
    });
  }

  ngOnDestroy(): void {
    this.observer?.disconnect();
  }

  close(): void {
    this.closed.emit();
  }

  onOverlayClick(event: MouseEvent): void {
    if ((event.target as HTMLElement).classList.contains('fixed')) {
      this.close();
    }
  }
}
