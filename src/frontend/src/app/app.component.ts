import { Component } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { HorizontalNavComponent } from './components/horizontal-nav/horizontal-nav.component';
import { UpdateNotificationComponent } from './components/ui/update-notification/update-notification.component';

@Component({
  selector: 'app-root',
  standalone: true,
  imports: [RouterOutlet, HorizontalNavComponent, UpdateNotificationComponent],
  templateUrl: './app.component.html',
  styleUrls: ['./app.component.css']
})
export class AppComponent {
  title = 'EEG Classifier';
}
