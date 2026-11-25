import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subscription } from 'rxjs';

import {
  Organization,
  OrganizationService,
} from '../../core/services/organization.service';
import { Project, ProjectService } from '../../core/services/project.service';
import {
  Bug,
  BugFilters,
  BugService,
  BugStatsResponse,
} from '../../core/services/bug.service';
import { BugDialogComponent } from './components/bug-dialog/bug-dialog.component';
import { BugDetailComponent } from './components/bug-detail/bug-detail.component';

@Component({
  selector: 'app-bug-tracker',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatButtonModule,
    MatIconModule,
    MatDialogModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
  ],
  templateUrl: './bug-tracker.component.html',
  styleUrl: './bug-tracker.component.scss',
})
export class BugTrackerComponent implements OnInit, OnDestroy {
  activeOrg: Organization | null = null;
  projects: Project[] = [];
  selectedProject: Project | null = null;

  bugs: Bug[] = [];
  stats: BugStatsResponse | null = null;
  totalCount = 0;
  isLoading = false;
  isProjectsLoading = false;
  errorMessage = '';

  // Filter state
  searchQuery = '';
  selectedStatus = '';
  selectedSeverity = '';
  selectedPriority = '';

  statuses = [
    { value: '', label: 'All Statuses' },
    { value: 'open', label: 'Open' },
    { value: 'in_progress', label: 'In Progress' },
    { value: 'resolved', label: 'Resolved' },
    { value: 'closed', label: 'Closed' },
    { value: 'wont_fix', label: 'Won\'t Fix' },
  ];

  severities = [
    { value: '', label: 'All Severities' },
    { value: 'critical', label: 'Critical' },
    { value: 'high', label: 'High' },
    { value: 'medium', label: 'Medium' },
    { value: 'low', label: 'Low' },
  ];

  priorities = [
    { value: '', label: 'All Priorities' },
    { value: 'critical', label: 'Critical' },
    { value: 'high', label: 'High' },
    { value: 'medium', label: 'Medium' },
    { value: 'low', label: 'Low' },
  ];

  private sub = new Subscription();

  constructor(
    private orgService: OrganizationService,
    private projectService: ProjectService,
    private bugService: BugService,
    private dialog: MatDialog
  ) {}

  ngOnInit(): void {
    this.sub.add(
      this.orgService.activeOrg$.subscribe((org) => {
        this.activeOrg = org;
        if (org) {
          this.loadProjects(org.id);
        } else {
          this.projects = [];
          this.selectedProject = null;
          this.bugs = [];
          this.stats = null;
        }
      })
    );
  }

  ngOnDestroy(): void {
    this.sub.unsubscribe();
  }

  loadProjects(orgId: string): void {
    this.isProjectsLoading = true;
    this.projectService.getProjects(orgId).subscribe({
      next: (projs) => {
        this.projects = projs;
        this.isProjectsLoading = false;
        if (projs.length > 0) {
          this.selectedProject = projs[0];
          this.loadBugsAndStats();
        } else {
          this.selectedProject = null;
          this.bugs = [];
          this.stats = null;
        }
      },
      error: () => {
        this.isProjectsLoading = false;
      },
    });
  }

  onProjectChange(projectId: string): void {
    const found = this.projects.find((p) => p.id === projectId);
    if (found) {
      this.selectedProject = found;
      this.loadBugsAndStats();
    }
  }

  loadBugsAndStats(): void {
    if (!this.selectedProject) return;
    this.isLoading = true;
    this.errorMessage = '';

    const filters: BugFilters = {
      status: this.selectedStatus || undefined,
      severity: this.selectedSeverity || undefined,
      priority: this.selectedPriority || undefined,
      search: this.searchQuery.trim() || undefined,
    };

    this.bugService.getBugs(this.selectedProject.id, filters).subscribe({
      next: (res) => {
        this.bugs = res.items;
        this.totalCount = res.total;
        this.isLoading = false;
      },
      error: () => {
        this.isLoading = false;
        this.errorMessage = 'Failed to load bugs.';
      },
    });

    this.bugService.getStats(this.selectedProject.id).subscribe({
      next: (stats) => {
        this.stats = stats;
      },
    });
  }

  openCreateBugDialog(): void {
    if (!this.selectedProject) return;

    const dialogRef = this.dialog.open(BugDialogComponent, {
      width: '650px',
      data: { projectId: this.selectedProject.id },
    });

    dialogRef.afterClosed().subscribe((result) => {
      if (result) {
        this.loadBugsAndStats();
      }
    });
  }

  openBugDetail(bug: Bug): void {
    const dialogRef = this.dialog.open(BugDetailComponent, {
      width: '680px',
      data: { bug },
    });

    dialogRef.afterClosed().subscribe(() => {
      this.loadBugsAndStats();
    });
  }

  deleteBug(bug: Bug, event: MouseEvent): void {
    event.stopPropagation();
    if (!this.selectedProject) return;
    if (confirm(`Are you sure you want to delete defect "${bug.bug_key}"?`)) {
      this.bugService.deleteBug(this.selectedProject.id, bug.id).subscribe({
        next: () => {
          this.loadBugsAndStats();
        },
        error: () => {
          this.errorMessage = 'Failed to delete bug.';
        },
      });
    }
  }
}
