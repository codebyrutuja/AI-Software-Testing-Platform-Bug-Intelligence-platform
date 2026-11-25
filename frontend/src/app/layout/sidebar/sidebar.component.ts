import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';
import { RouterLink, RouterLinkActive } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';

interface NavItem {
  label: string;
  icon: string;
  route: string;
  disabled?: boolean;
  badge?: string;
}

@Component({
  selector: 'app-sidebar',
  standalone: true,
  imports: [
    CommonModule,
    RouterLink,
    RouterLinkActive,
    MatIconModule,
    MatTooltipModule,
  ],
  templateUrl: './sidebar.component.html',
  styleUrl: './sidebar.component.scss',
})
export class SidebarComponent {
  @Input() isCollapsed = false;

  navItems: NavItem[] = [
    { label: 'Dashboard', icon: 'dashboard', route: '/dashboard' },
    { label: 'Projects', icon: 'folder', route: '/projects' },
    { label: 'Requirements', icon: 'assignment', route: '/requirements' },
    { label: 'Test Cases', icon: 'science', route: '/test-cases' },
    { label: 'Test Runs', icon: 'play_circle', route: '/test-runs' },
    { label: 'Bug Tracker', icon: 'bug_report', route: '/bugs' },
    { label: 'Settings', icon: 'settings', route: '/settings', disabled: true, badge: 'Soon' },
  ];
}
