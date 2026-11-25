import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
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
  TestCase,
  TestCaseFilters,
  TestCaseService,
  TestSuite,
} from '../../core/services/test-case.service';
import { SuiteDialogComponent } from './components/suite-dialog/suite-dialog.component';
import { TestCaseDialogComponent } from './components/test-case-dialog/test-case-dialog.component';
import { TestCaseDetailComponent } from './components/test-case-detail/test-case-detail.component';

@Component({
  selector: 'app-test-cases',
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
  templateUrl: './test-cases.component.html',
  styleUrl: './test-cases.component.scss',
})
export class TestCasesComponent implements OnInit, OnDestroy {
  activeOrg: Organization | null = null;
  projects: Project[] = [];
  selectedProject: Project | null = null;

  suites: TestSuite[] = [];
  selectedSuiteId: string | null = null;

  testCases: TestCase[] = [];
  totalCount = 0;
  isLoading = false;
  isProjectsLoading = false;
  errorMessage = '';

  // Filter state
  searchQuery = '';
  selectedType = '';
  selectedPriority = '';
  selectedStatus = '';

  testTypes = [
    { value: '', label: 'All Types' },
    { value: 'manual', label: 'Manual' },
    { value: 'automated', label: 'Automated' },
    { value: 'regression', label: 'Regression' },
    { value: 'smoke', label: 'Smoke' },
    { value: 'sanity', label: 'Sanity' },
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
    { value: 'active', label: 'Active' },
    { value: 'draft', label: 'Draft' },
    { value: 'deprecated', label: 'Deprecated' },
  ];

  private sub = new Subscription();

  constructor(
    private orgService: OrganizationService,
    private projectService: ProjectService,
    private tcService: TestCaseService,
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
          this.suites = [];
          this.testCases = [];
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
          this.loadSuitesAndCases();
        } else {
          this.selectedProject = null;
          this.suites = [];
          this.testCases = [];
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
      this.selectedSuiteId = null;
      this.loadSuitesAndCases();
    }
  }

  loadSuitesAndCases(): void {
    if (!this.selectedProject) return;

    this.tcService.getSuites(this.selectedProject.id).subscribe({
      next: (suites) => {
        this.suites = suites;
      },
    });

    this.loadTestCases();
  }

  loadTestCases(): void {
    if (!this.selectedProject) return;

    this.isLoading = true;
    this.errorMessage = '';

    const filters: TestCaseFilters = {
      suite_id: this.selectedSuiteId || undefined,
      test_type: this.selectedType || undefined,
      priority: this.selectedPriority || undefined,
      status: this.selectedStatus || undefined,
      search: this.searchQuery.trim() || undefined,
    };

    this.tcService.getTestCases(this.selectedProject.id, filters).subscribe({
      next: (res) => {
        this.testCases = res.items;
        this.totalCount = res.total;
        this.isLoading = false;
      },
      error: (err) => {
        this.errorMessage = err.error?.detail || 'Failed to load test cases.';
        this.isLoading = false;
      },
    });
  }

  selectSuite(suiteId: string | null): void {
    this.selectedSuiteId = suiteId;
    this.loadTestCases();
  }

  openCreateSuiteDialog(): void {
    if (!this.selectedProject) return;

    const dialogRef = this.dialog.open(SuiteDialogComponent, {
      width: '460px',
      data: {
        projectId: this.selectedProject.id,
        existingSuites: this.suites,
      },
    });

    dialogRef.afterClosed().subscribe((created: TestSuite | undefined) => {
      if (created) {
        this.suites = [...this.suites, created];
      }
    });
  }

  openCreateCaseDialog(): void {
    if (!this.selectedProject) return;

    const dialogRef = this.dialog.open(TestCaseDialogComponent, {
      width: '700px',
      maxHeight: '90vh',
      data: {
        projectId: this.selectedProject.id,
        suites: this.suites,
        preselectedSuiteId: this.selectedSuiteId,
      },
    });

    dialogRef.afterClosed().subscribe((created: TestCase | undefined) => {
      if (created) {
        this.testCases = [created, ...this.testCases];
        this.totalCount += 1;
        // update suite count locally
        if (created.suite_id) {
          const s = this.suites.find((x) => x.id === created.suite_id);
          if (s) s.case_count += 1;
        }
      }
    });
  }

  viewTestCase(tc: TestCase): void {
    if (!this.selectedProject) return;

    const dialogRef = this.dialog.open(TestCaseDetailComponent, {
      width: '680px',
      maxHeight: '90vh',
      data: {
        projectId: this.selectedProject.id,
        testCase: tc,
        suites: this.suites,
      },
    });

    dialogRef.afterClosed().subscribe((res) => {
      if (!res) return;
      if (res.action === 'deleted') {
        this.testCases = this.testCases.filter((t) => t.id !== res.testCaseId);
        this.totalCount = Math.max(0, this.totalCount - 1);
        this.tcService.getSuites(this.selectedProject!.id).subscribe((s) => (this.suites = s));
      } else if (res.action === 'updated') {
        const idx = this.testCases.findIndex((t) => t.id === res.testCase.id);
        if (idx !== -1) {
          this.testCases[idx] = res.testCase;
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

  getTypeClass(type: string): string {
    switch (type) {
      case 'automated':
        return 'bg-emerald-100 text-emerald-700 border-emerald-200';
      case 'regression':
        return 'bg-blue-100 text-blue-700 border-blue-200';
      case 'smoke':
        return 'bg-orange-100 text-orange-700 border-orange-200';
      case 'sanity':
        return 'bg-cyan-100 text-cyan-700 border-cyan-200';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  }
}
