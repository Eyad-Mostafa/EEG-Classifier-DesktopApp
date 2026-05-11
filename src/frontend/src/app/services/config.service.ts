import { Injectable } from '@angular/core';
import { environment } from '../../environments/environment';

// 1.This code runs instantly when the file is loaded, 
// long before Angular's Router can wipe the URL.
let cachedPort: number | null = null;
const currentUrl = window.location.href;
const match = currentUrl.match(/[?&]apiPort=(\d+)/);

if (match) {
  cachedPort = parseInt(match[1], 10);
  // Save it so it survives page reloads or navigation
  sessionStorage.setItem('eeg_api_port', cachedPort.toString());
} else {
  // If not in URL (e.g., after navigation), check if we saved it previously
  const saved = sessionStorage.getItem('eeg_api_port');
  if (saved) {
    cachedPort = parseInt(saved, 10);
  }
}

@Injectable({
  providedIn: 'root'
})
export class ConfigService {
  private apiPort: number = 8000; // Default fallback (for ng serve)
  private apiUrl: string = '';

  constructor() {
    this.initialize();
  }

  private initialize() {
    // 2. Use the early-caught port
    if (cachedPort) {
      this.apiPort = cachedPort;
      console.log(`🔌 Angular connected to Dynamic Port: ${this.apiPort}`);
    } else {
      console.warn('⚠️ No port found in URL or cache, using default: 8000');
    }

    // 3. Construct the full API URL
    this.apiUrl = `${environment.apiHost}:${this.apiPort}/api`;
  }

  // Other services will call this to get the base URL
  getApiUrl(): string {
    return this.apiUrl;
  }
}