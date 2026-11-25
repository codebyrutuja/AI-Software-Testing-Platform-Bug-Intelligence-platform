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
  DocumentUploadResponse,
  Requirement,
  RequirementFilters,
  RequirementService,
} from '../../core/services/requirement.service';
import { UploadDialogComponent } from './components/upload-dialog/upload-dialog.component';
import { RequirementDialogComponent } from './components/requirement-dialog/requirement-dialog.component';
import { RequirementDetailComponent } from './components/requirement-detail/requirement-detail.component';

@Component({
  selector: 'app-requirements',
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
  templateUrl: './requirements.component.html',
  styleUrl: './requirements.component.scss',
})
export class RequirementsComponent implements OnInit, OnDestroy {
  activeOrg: Organization | null = null;
  projects: Project[] = [];
  selectedProject: Project | null = null;

  requirements: Requirement[] = [];
  totalCount = 0;
  isLoading = false;
  isProjectsLoading = false;
  errorMessage = '';

  // Filter state
  searchQuery = '';
  selectedCategory = '';
  selectedPriority = '';
  selectedStatus = '';

  categories = [
    { value: '', label: 'All Categories' },
    { value: 'functional', label: 'Functional' },
    { value: 'non_functional', label: 'Non-Functional' },
    { value: 'security', label: 'Security' },
    { value: 'ui_ux', label: 'UI / UX' },
    { value: 'performance', label: 'Performance' },
  ];

  priorities = [
    { value: '', label: 'All Priorities' },
    { value: 'critical', label: 'Critical' },
    { value: 'high', label: 'High' },
    { value: 'medium', label: 'Medium' },
    { value: 'low', label: 'Low' },
  ];

  statuses = [
    { value: '', label: 'All Statuses' },
    { value: 'draft', label: 'Draft' },
    { value: 'approved', label: 'Approved' },
    { value: 'deprecated', label: 'Deprecated' },
  ];

  private sub = new Subscription();

  constructor(
    private orgService: OrganizationService,
    private projectService: ProjectService,
    private reqService: RequirementService,
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
          this.requirements = [];
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
          this.loadRequirements();
        } else {
          this.selectedProject = null;
          this.requirements = [];
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
      this.loadRequirements();
    }
  }

  loadRequirements(): void {
    if (!this.selectedProject) return;

    this.isLoading = true;
    this.errorMessage = '';

    const filters: RequirementFilters = {
      search: this.searchQuery.trim() || undefined,
      category: this.selectedCategory || undefined,
      priority: this.selectedPriority || undefined,
      status: this.selectedStatus || undefined,
    };

    this.reqService.listRequirements(this.selectedProject.id, filters).subscribe({
      next: (res) => {
        this.requirements = res.items;
        this.totalCount = res.total;
        this.isLoading = false;
      },
      error: (err) => {
        this.errorMessage = err.error?.detail || 'Failed to load requirements.';
        this.isLoading = false;
      },
    });
  }

  onSearch(): void {
    this.loadRequirements();
  }

  openUploadDialog(): void {
    if (!this.selectedProject) return;

    const dialogRef = this.dialog.open(UploadDialogComponent, {
      width: '540px',
      data: { projectId: this.selectedProject.id },
    });

    dialogRef.afterClosed().subscribe((result: DocumentUploadResponse | undefined) => {
      if (result && result.requirements) {
        // Prepend parsed requirements into current view
        this.requirements = [...result.requirements, ...this.requirements];
        this.totalCount += result.extracted_count;
      }
    });
  }

  openCreateDialog(): void {
    if (!this.selectedProject) return;

    const dialogRef = this.dialog.open(RequirementDialogComponent, {
      width: '560px',
      data: { projectId: this.selectedProject.id },
    });

    dialogRef.afterClosed().subscribe((created: Requirement | undefined) => {
      if (created) {
        this.requirements = [created, ...this.requirements];
        this.totalCount += 1;
      }
    });
  }

  viewRequirement(req: Requirement): void {
    if (!this.selectedProject) return;

    const dialogRef = this.dialog.open(RequirementDetailComponent, {
      width: '600px',
      data: {
        projectId: this.selectedProject.id,
        requirement: req,
      },
    });

    dialogRef.afterClosed().subscribe((res) => {
      if (!res) return;
      if (res.action === 'deleted') {
        this.requirements = this.requirements.filter((r) => r.id !== res.requirementId);
        this.totalCount = Math.max(0, this.totalCount - 1);
      } else if (res.action === 'updated') {
        const idx = this.requirements.findIndex((r) => r.id === res.requirement.id);
        if (idx !== -1) {
          this.requirements[idx] = res.requirement;
        }
      }
    });
  }

  getPriorityClass(priority: string): string {
    switch (priority) {
      case 'critical':
        return 'bg-purple-100 text-purple-700 border-purple-200';
      case 'high':
        return 'bg-red-100 text-red-700 border-red-200';
      case 'medium':
        return 'bg-amber-100 text-amber-700 border-amber-200';
      case 'low':
        return 'bg-green-100 text-green-700 border-green-200';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  }

  getCategoryLabel(category: string): string {
    switch (category) {
      case 'ui_ux':
        return 'UI / UX';
      case 'non_functional':
        return 'Non-Functional';
      default:
        return category.charAt(0).toUpperCase() + category.slice(1);
    }
  }
}
