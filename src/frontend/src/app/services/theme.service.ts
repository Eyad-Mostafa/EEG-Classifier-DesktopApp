import { Injectable } from '@angular/core';
import { BehaviorSubject } from 'rxjs';

@Injectable({
  providedIn: 'root'
})
export class ThemeService {
  // true = Dark Mode, false = Light Mode
  private darkMode = new BehaviorSubject<boolean>(this.getInitialTheme());
  isDarkMode$ = this.darkMode.asObservable();

  constructor() {
    // Apply initial theme to Body
    this.applyTheme(this.darkMode.value);
  }

  toggleTheme() {
    const newMode = !this.darkMode.value;
    this.darkMode.next(newMode);
    this.applyTheme(newMode);
    localStorage.setItem('theme', newMode ? 'dark' : 'light');
  }

  private getInitialTheme(): boolean {
    const saved = localStorage.getItem('theme');
    if (saved) return saved === 'dark';
    return window.matchMedia('(prefers-color-scheme: dark)').matches;
  }

  private applyTheme(isDark: boolean) {
    if (isDark) {
      document.documentElement.classList.add('dark');
    } else {
      document.documentElement.classList.remove('dark');
    }
  }
  
  // Helper to get current value synchronously if needed
  get currentTheme() {
    return this.darkMode.value;
  }
}