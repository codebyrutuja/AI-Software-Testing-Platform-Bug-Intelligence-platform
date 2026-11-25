import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
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
  CreateTestRunRequest,
  TestRun,
  TestRunService,
} from '../../core/services/test-run.service';
import { RunDialogComponent } from './components/run-dialog/run-dialog.component';

@Component({
  selector: 'app-test-runs',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    MatButtonModule,
    MatIconModule,
    MatDialogModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
  ],
  templateUrl: './test-runs.component.html',
  styleUrl: './test-runs.component.scss',
})
export class TestRunsComponent implements OnInit, OnDestroy {
  activeOrg: Organization | null = null;
  projects: Project[] = [];
  selectedProject: Project | null = null;

  runs: TestRun[] = [];
  totalCount = 0;
  isLoading = false;
  isProjectsLoading = false;
  errorMessage = '';

  selectedStatus = '';
  statuses = [
    { value: '', label: 'All Statuses' },
    { value: 'planned', label: 'Planned' },
    { value: 'in_progress', label: 'In Progress' },
    { value: 'completed', label: 'Completed' },
    { value: 'aborted', label: 'Aborted' },
  ];

  private sub = new Subscription();

  constructor(
    private orgService: OrganizationService,
    private projectService: ProjectService,
    private runService: TestRunService,
    private dialog: MatDialog,
    private router: Router
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
          this.runs = [];
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
          this.loadRuns();
        } else {
          this.selectedProject = null;
          this.runs = [];
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
      this.loadRuns();
    }
  }

  loadRuns(): void {
    if (!this.selectedProject) return;
    this.isLoading = true;
    this.errorMessage = '';

    this.runService
      .getRuns(this.selectedProject.id, this.selectedStatus || undefined)
      .subscribe({
        next: (res) => {
          this.runs = res.items;
          this.totalCount = res.total;
          this.isLoading = false;
        },
        error: () => {
          this.isLoading = false;
          this.errorMessage = 'Failed to load test runs.';
        },
      });
  }

  openCreateRunDialog(): void {
    if (!this.selectedProject) return;

    const dialogRef = this.dialog.open(RunDialogComponent, {
      width: '600px',
      data: { projectId: this.selectedProject.id },
    });

    dialogRef.afterClosed().subscribe((result: CreateTestRunRequest) => {
      if (result) {
        this.runService.createRun(this.selectedProject!.id, result).subscribe({
          next: (created) => {
            this.loadRuns();
            // Automatically navigate to execution runner
            this.executeRun(created);
          },
          error: (err) => {
            this.errorMessage = err?.error?.detail || 'Failed to create test run.';
          },
        });
      }
    });
  }

  executeRun(run: TestRun): void {
    if (!this.selectedProject) return;
    this.router.navigate(['/test-runs', this.selectedProject.id, run.id, 'execute']);
  }

  deleteRun(run: TestRun, event: MouseEvent): void {
    event.stopPropagation();
    if (!this.selectedProject) return;
    if (confirm(`Are you sure you want to delete test run "${run.name}"?`)) {
      this.runService.deleteRun(this.selectedProject.id, run.id).subscribe({
        next: () => {
          this.loadRuns();
        },
        error: () => {
          this.errorMessage = 'Failed to delete test run.';
        },
      });
    }
  }

  getPassedPercentage(run: TestRun): number {
    if (run.total_count === 0) return 0;
    return Math.round((run.passed_count / run.total_count) * 100);
  }
}
