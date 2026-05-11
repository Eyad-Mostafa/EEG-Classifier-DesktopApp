import { Component, OnInit, HostListener } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterModule, Router, NavigationEnd } from '@angular/router';
import { WorkflowService } from '../../services/workflow.service';
import { NavItem } from '../../models/ui/navigation.ui';
import { filter } from 'rxjs/operators';
import { ThemeService } from '../../services/theme.service';

@Component({
  selector: 'app-horizontal-nav',
  standalone: true,
  imports: [CommonModule, RouterModule],
  templateUrl: './horizontal-nav.component.html',
  styleUrls: [],
})
export class HorizontalNavComponent implements OnInit {
  isDarkMode = false;
  currentRoute = '';

  navItems: any[] = [
    { label: 'Choose File',        path: '/upload',        icon: 'folder_open',   dataNav: 'choose',      disabled: false },
    { label: 'Config',        path: '/config',        icon: 'tune',          dataNav: 'config',      disabled: true },
    { 
      label: 'Preprocessing', 
      path: null, 
      icon: 'science', 
      dataNav: 'preprocess', 
      isOpen: false,         // Keeps your dropdown working!
      children: [
        { label: 'Configure', path: '/preprocess', disabled: true },
        { label: 'Results',   path: '/results',    disabled: true }
      ]
    },
    { label: 'Analysis',      path: '/analysis',      icon: 'analytics',     dataNav: 'analysis',    disabled: true },
    { label: 'Visualization', path: '/visualization', icon: 'visibility',    dataNav: 'viz',         disabled: true },
    { label: 'AI Models',     path: '/ai-models',     icon: 'model_training',dataNav: 'ai',          disabled: true },
    { label: 'Algorithms',    path: '/algorithms',    icon: 'library_books', dataNav: 'algorithms',  disabled: false },
  ];

  constructor(
    public workflowService: WorkflowService,
    private router: Router,
    private themeService: ThemeService,
  ) {
    this.router.events
      .pipe(filter((event) => event instanceof NavigationEnd))
      .subscribe((event: any) => {
        this.currentRoute = event.url;
      });
  }

  isParentDisabled(item: any): boolean {
    if (!item.children) return !!item.disabled;
    // Returns true ONLY if every single child is disabled
    return item.children.every((child: any) => child.disabled);
  }

  toggleDropdown(item: any, event: Event) {
    event.stopPropagation(); // Stops the document click listener from firing immediately
    
    const wasOpen = item.isOpen;
    // Optional: Close any other open dropdowns first
    this.navItems.forEach(n => { if (n.children) n.isOpen = false; });
    // Toggle this one
    item.isOpen = !wasOpen;
  }

  @HostListener('document:click')
  clickout() {
    this.navItems.forEach(item => {
      if (item.children) item.isOpen = false;
    });
  }

  ngOnInit(): void {
    this.themeService.isDarkMode$.subscribe(
      (isDark) => (this.isDarkMode = isDark)
    );

    this.workflowService.navState$.subscribe((state) => {
      this.navItems.forEach((item) => {
        if (item.children) {
          item.children.forEach((child: any) => {
            if (state[child.path] !== undefined) {
              child.disabled = state[child.path];
            }
          });
        } else {
          if (state[item.path] !== undefined) {
            item.disabled = state[item.path];
          }
        }
      });
    });
  }

  toggleDarkMode() {
    this.themeService.toggleTheme();
  }

  goTo(item: any, event?: Event) {
    if (event) event.stopPropagation();
    if (item.disabled) return;

    if (!item.children) {
      this.router.navigate([item.path]);
      // Close dropdowns after navigation
      this.navItems.forEach(navItem => {
        if (navItem.children) navItem.isOpen = false;
      });
    }
  }

  goToUpload() {
    this.router.navigate(['/upload']);
  }

  goToSettings() {
    this.router.navigate(['/settings']);
  }

  // Optional helper to check if current route is inside a dropdown
  isChildActive(item: any): boolean {
    if (!item.children) return false;
    return item.children.some((child: any) => child.path === this.currentRoute);
  }
}