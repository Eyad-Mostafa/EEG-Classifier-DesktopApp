
import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { ConfigService } from './config.service';

@Injectable({
  providedIn: 'root',
})

export class SystemService {
  
  constructor(private http: HttpClient, private configService: ConfigService) {}

  deleteAllHistory(): Observable<any> {
    return this.http.delete(`${this.configService.getApiUrl()}/system/wipe`);
  }
}