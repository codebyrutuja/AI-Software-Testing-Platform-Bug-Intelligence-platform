import { Component, EventEmitter, Input, OnInit, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router } from '@angular/router';
import { MatToolbarModule } from '@angular/material/toolbar';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatDividerModule } from '@angular/material/divider';
import { AuthService, User } from '../../core/services/auth.service';
import {
  Organization,
  OrganizationService,
} from '../../core/services/organization.service';

@Component({
  selector: 'app-topbar',
  standalone: true,
  imports: [
    CommonModule,
    MatToolbarModule,
    MatButtonModule,
    MatIconModule,
    MatMenuModule,
    MatDividerModule,
  ],
  templateUrl: './topbar.component.html',
  styleUrl: './topbar.component.scss',
})
export class TopbarComponent implements OnInit {
  @Input() isCollapsed = false;
  @Output() toggleSidebar = new EventEmitter<void>();

  currentUser: User | null = null;
  activeOrg: Organization | null = null;
  organizations: Organization[] = [];

  constructor(
    private authService: AuthService,
    private orgService: OrganizationService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.authService.currentUser$.subscribe((user) => {
      this.currentUser = user;
    });

    this.orgService.activeOrg$.subscribe((org) => {
      this.activeOrg = org;
    });

    this.loadOrganizations();
  }

  loadOrganizations(): void {
    this.orgService.getMyOrganizations().subscribe({
      next: (orgs) => {
        this.organizations = orgs;
      },
      error: (err) => console.error('Failed to load organizations', err),
    });
  }

  selectOrg(org: Organization): void {
    this.orgService.setActiveOrg(org);
  }

  promptCreateOrg(): void {
    const orgName = prompt('Enter new Organization name:');
    if (orgName && orgName.trim().length >= 2) {
      this.orgService
        .createOrganization({ name: orgName.trim() })
        .subscribe({
          next: (newOrg) => {
            this.loadOrganizations();
            this.selectOrg(newOrg);
          },
          error: (err) => alert(err.error?.detail || 'Failed to create organization.'),
        });
    }
  }

  onToggle(): void {
    this.toggleSidebar.emit();
  }

  logout(): void {
    this.authService.logout();
  }
}
