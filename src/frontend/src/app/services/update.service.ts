import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject } from 'rxjs';

export const CURRENT_APP_VERSION = '2.1.1';

export interface VersionInfo {
  latest: string;
  downloadUrl: string;
  notes?: string;
}

@Injectable({
  providedIn: 'root'
})
export class UpdateService {
  private versionUrl = 'https://raw.githubusercontent.com/Eyad-Mostafa/EEG-Classifier-DesktopApp/main/version.json';

  private updateAvailableSubject = new BehaviorSubject<VersionInfo | null>(null);
  updateAvailable$ = this.updateAvailableSubject.asObservable();

  constructor(private http: HttpClient) {
    this.checkForUpdates();
  }

  checkForUpdates() {
    this.http.get<VersionInfo>(this.versionUrl).subscribe({
      next: (info) => {
        if (info.latest !== CURRENT_APP_VERSION) {
          console.log(`Update available: ${info.latest}`);
          this.updateAvailableSubject.next(info);
        }
      },
      error: (err) => console.error('Failed to check for updates', err)
    });
  }
}