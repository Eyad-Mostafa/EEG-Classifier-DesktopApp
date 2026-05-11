import { Component, Input } from '@angular/core'; // Import Input
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-loader',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './app-loader.component.html',
  styleUrls: ['./app-loader.component.css']
})
export class AppLoaderComponent {
  @Input() message: string = '';
  @Input() subMessage: string = '';
}