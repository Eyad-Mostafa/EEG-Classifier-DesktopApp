import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { UpdateService, VersionInfo } from '../../../services/update.service';

@Component({
  selector: 'app-update-notification',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './update-notification.component.html',
  styleUrls: ['./update-notification.component.css']
})
export class UpdateNotificationComponent {
  updateInfo: VersionInfo | null = null;

  constructor(private updateService: UpdateService) {
    this.updateService.updateAvailable$.subscribe(info => {
      this.updateInfo = info;
    });
  }

  dismiss() {
    this.updateInfo = null;
  }
}