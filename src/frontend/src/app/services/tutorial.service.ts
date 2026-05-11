import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({ providedIn: 'root' })
export class TutorialService {
  private tutorialSeenKey = 'tutorial_seen';
  private onboardingSeenKey = 'onboarding_seen';

  private aiTutorialSeenKey = 'ai_tutorial_seen';
  private showAiTutorialSubject = new BehaviorSubject<boolean>(false);
  showAiTutorial$ = this.showAiTutorialSubject.asObservable();

  private showTutorialSubject = new BehaviorSubject<boolean>(false);
  showTutorial$ = this.showTutorialSubject.asObservable();

  private showOnboardingSubject = new BehaviorSubject<boolean>(false);
  showOnboarding$ = this.showOnboardingSubject.asObservable();

  constructor() {
    const tutorialSeen = localStorage.getItem(this.tutorialSeenKey) === 'true';
    this.showTutorialSubject.next(!tutorialSeen);

    const onboardingSeen = localStorage.getItem(this.onboardingSeenKey) === 'true';
    this.showOnboardingSubject.next(!onboardingSeen);

    const aiTutorialSeen = localStorage.getItem(this.aiTutorialSeenKey) === 'true';
    this.showAiTutorialSubject.next(!aiTutorialSeen);
  }

  markAsSeen(): void {
    localStorage.setItem(this.tutorialSeenKey, 'true');
    this.showTutorialSubject.next(false);
  }

  resetTutorial(): void {
    localStorage.setItem(this.tutorialSeenKey, 'false');
    this.showTutorialSubject.next(true);
  }

  markOnboardingSeen(): void {
    localStorage.setItem(this.onboardingSeenKey, 'true');
    this.showOnboardingSubject.next(false);
  }

  resetOnboarding(): void {
    localStorage.setItem(this.onboardingSeenKey, 'false');
    this.showOnboardingSubject.next(true);
  }

  markAiTutorialSeen(): void {
    localStorage.setItem(this.aiTutorialSeenKey, 'true');
    this.showAiTutorialSubject.next(false);
  }

  resetAiTutorial(): void {
    localStorage.setItem(this.aiTutorialSeenKey, 'false');
    this.showAiTutorialSubject.next(true);
  }
}