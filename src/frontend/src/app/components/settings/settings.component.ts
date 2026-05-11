import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ThemeService } from '../../services/theme.service';
import { UpdateService, CURRENT_APP_VERSION, VersionInfo } from '../../services/update.service';
import { SystemService } from '../../services/system.service';
import { WorkflowService } from '../../services/workflow.service';
import { TutorialService } from '../../services/tutorial.service';
import { ConfirmDialogComponent } from "../ui/confirm-dialog/confirm-dialog.component";

interface TeamMember {
  name: string;
  initials: string;
  email: string;
  linkedin: string;
}

@Component({
  selector: 'app-settings',
  standalone: true,
  imports: [CommonModule, FormsModule, ConfirmDialogComponent],
  templateUrl: './settings.component.html',
  styleUrls: []
})
export class SettingsComponent implements OnInit {
  activeTab: 'preferences' | 'about' = 'preferences';
  isDarkMode = false;

  showDeleteConfirm = false;
  isDeletingHistory = false;

  currentVersion = CURRENT_APP_VERSION;
  updateInfo: VersionInfo | null = null;
  isCheckingForUpdates = false;

  teamMembers: TeamMember[] = [
    {
      name: 'Eyad Mostafa',
      initials: 'EM',
      email: 'mailto:eyadmostafa464@gmail.com',
      linkedin: 'https://linkedin.com/in/EyadMostafa'
    },
    {
      name: 'Abobaker',
      initials: 'A',
      email: 'mailto:abobaker.mohamed.email@gmail.com',
      linkedin: 'https://linkedin.com/in/abobaker-mohamed'
    },
    {
      name: 'Menna',
      initials: 'M',
      email: 'mailto:mennasabra3@gmail.com',
      linkedin: 'https://www.linkedin.com/in/mennaallahahmed6/'
    },
    {
      name: 'Omar',
      initials: 'O',
      email: 'omarn5277@gmail.com',
      linkedin: 'https://www.linkedin.com/in/omarnasser1?utm_source=share_via&utm_content=profile&utm_medium=member_ios'
    }
  ];

  constructor(
    private themeService: ThemeService,
    private updateService: UpdateService,
    private systemService: SystemService,
    private workflowService: WorkflowService,
    private tutorialService: TutorialService,
    private router: Router
  ) { }

  ngOnInit(): void {
    this.themeService.isDarkMode$.subscribe(isDark => this.isDarkMode = isDark);
    this.updateService.updateAvailable$.subscribe(info => this.updateInfo = info);
  }

  setTab(tab: 'preferences' | 'about'): void {
    this.activeTab = tab;
  }

  toggleTheme(): void {
    this.themeService.toggleTheme();
  }

  // 👈 Instantly route to upload page instead of waiting
  resetOnboarding(): void {
    this.tutorialService.resetOnboarding();
    this.router.navigate(['/upload']);
  }

  checkForUpdates(): void {
    this.isCheckingForUpdates = true;
    this.updateService.checkForUpdates();
    setTimeout(() => this.isCheckingForUpdates = false, 1500);
  }

  openDeleteConfirmation(): void {
    this.showDeleteConfirm = true;
  }

  cancelDelete(): void {
    this.showDeleteConfirm = false;
  }

  executeDeleteHistory(): void {
    this.isDeletingHistory = true;

    this.systemService.deleteAllHistory().subscribe({
      next: () => {
        this.isDeletingHistory = false;
        this.showDeleteConfirm = false;
        this.workflowService.clearWorkflow();
        this.showNotification('All history and data cleared successfully!', true);
      },
      error: (err) => {
        console.error('Failed to clear history:', err);
        this.isDeletingHistory = false;
        this.showDeleteConfirm = false;
        this.showNotification('Failed to clear database. Please try again.', false);
      }
    });
  }

  showNotification(message: string, isSuccess: boolean = true): void {
    const notification = document.createElement('div');
    const bgColor = isSuccess ? 'bg-green-500' : 'bg-red-500';
    const icon = isSuccess ? 'check_circle' : 'error_outline';
    notification.className = `fixed top-4 right-4 ${bgColor} text-white px-4 py-2 rounded-lg shadow-lg z-[9999] transition-all duration-300 flex items-center gap-2`;
    notification.innerHTML = `<i class="material-icons text-sm">${icon}</i> <span class="text-sm font-medium">${message}</span>`;
    document.body.appendChild(notification);
    setTimeout(() => {
      notification.style.opacity = '0';
      setTimeout(() => notification.remove(), 300);
    }, 3000);
  }
}