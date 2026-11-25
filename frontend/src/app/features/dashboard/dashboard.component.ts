import {
  Component,
  OnInit,
  AfterViewInit,
  ViewChild,
  ElementRef,
  OnDestroy,
} from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { MatCardModule } from '@angular/material/card';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import {
  Chart,
  ArcElement,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
  DoughnutController,
  BarController,
} from 'chart.js';

// Register only what we use — keeps bundle small
Chart.register(
  ArcElement,
  BarElement,
  CategoryScale,
  LinearScale,
  Tooltip,
  Legend,
  DoughnutController,
  BarController,
);

import { AuthService, User } from '../../core/services/auth.service';
import { Organization, OrganizationService } from '../../core/services/organization.service';
import { ProjectService } from '../../core/services/project.service';
import {
  AnalyticsService,
  AnalyticsDashboardResponse,
} from '../../core/services/analytics.service';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    MatCardModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
  ],
  templateUrl: './dashboard.component.html',
  styleUrl: './dashboard.component.scss',
})
export class DashboardComponent implements OnInit, OnDestroy {
  currentUser: User | null = null;
  activeOrg: Organization | null = null;

  // Projects dropdown
  projects: any[] = [];
  selectedProjectId: string | null = null;

  // State
  isLoading = false;
  errorMessage: string | null = null;
  exportMenuOpen = false;
  chartsReady = false;

  // Analytics payload
  analytics: AnalyticsDashboardResponse | null = null;

  // Chart instances (destroyed on component destroy to avoid memory leaks)
  private runChart: Chart | null = null;
  private bugSevChart: Chart | null = null;
  private bugStatusChart: Chart | null = null;
  private coverageChart: Chart | null = null;

  constructor(
    private authService: AuthService,
    private orgService: OrganizationService,
    private projectService: ProjectService,
    private analyticsService: AnalyticsService,
  ) {}

  ngOnInit(): void {
    this.authService.currentUser$.subscribe((u) => (this.currentUser = u));
    this.orgService.activeOrg$.subscribe((org) => {
      this.activeOrg = org;
      if (org) {
        this.loadProjects(org.id);
      }
    });
  }

  ngOnDestroy(): void {
    this.destroyCharts();
  }

  private destroyCharts(): void {
    [this.runChart, this.bugSevChart, this.bugStatusChart, this.coverageChart].forEach(
      (c) => c?.destroy(),
    );
    this.runChart = null;
    this.bugSevChart = null;
    this.bugStatusChart = null;
    this.coverageChart = null;
  }

  loadProjects(orgId: string): void {
    this.projectService.getProjects(orgId).subscribe({
      next: (resp: any) => {
        this.projects = Array.isArray(resp) ? resp : (resp.projects || []);
        if (this.projects.length > 0) {
          this.selectedProjectId = this.projects[0].id;
          this.loadAnalytics();
        }
      },
      error: () => (this.projects = []),
    });
  }

  onProjectChange(projectId: string): void {
    this.selectedProjectId = projectId;
    this.loadAnalytics();
  }

  loadAnalytics(): void {
    if (!this.selectedProjectId) return;
    this.isLoading = true;
    this.errorMessage = null;
    this.chartsReady = false;

    this.analyticsService.getDashboard(this.selectedProjectId).subscribe({
      next: (data) => {
        this.analytics = data;
        this.isLoading = false;
        // Allow Angular to render canvas elements, then draw charts
        setTimeout(() => this.buildCharts(data), 50);
      },
      error: (err) => {
        this.errorMessage = err?.error?.detail || 'Failed to load analytics data.';
        this.isLoading = false;
      },
    });
  }

  private getCanvas(id: string): HTMLCanvasElement | null {
    return document.getElementById(id) as HTMLCanvasElement | null;
  }

  buildCharts(data: AnalyticsDashboardResponse): void {
    this.destroyCharts();

    // ── Run history grouped bar ───────────────────────────────────────────────
    const runCanvas = this.getCanvas('runChart');
    if (runCanvas) {
      this.runChart = new Chart(runCanvas, {
        type: 'bar',
        data: {
          labels: data.run_history.map((r) => r.run_key),
          datasets: [
            { label: 'Passed',  data: data.run_history.map((r) => r.passed_count),  backgroundColor: '#22c55e' },
            { label: 'Failed',  data: data.run_history.map((r) => r.failed_count),  backgroundColor: '#ef4444' },
            { label: 'Blocked', data: data.run_history.map((r) => r.blocked_count), backgroundColor: '#f59e0b' },
            { label: 'Skipped', data: data.run_history.map((r) => r.skipped_count), backgroundColor: '#94a3b8' },
          ],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: 'top' } },
          scales: { y: { beginAtZero: true, ticks: { stepSize: 1 } } },
        },
      });
    }

    // ── Bug severity doughnut ─────────────────────────────────────────────────
    const sevCanvas = this.getCanvas('bugSevChart');
    if (sevCanvas) {
      this.bugSevChart = new Chart(sevCanvas, {
        type: 'doughnut',
        data: {
          labels: ['Critical', 'High', 'Medium', 'Low'],
          datasets: [{
            data: [
              data.bug_severity.critical,
              data.bug_severity.high,
              data.bug_severity.medium,
              data.bug_severity.low,
            ],
            backgroundColor: ['#dc2626', '#f97316', '#eab308', '#22c55e'],
            hoverOffset: 8,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          plugins: { legend: { position: 'right' } },
        },
      });
    }

    // ── Bug status horizontal bar ─────────────────────────────────────────────
    const staCanvas = this.getCanvas('bugStatusChart');
    if (staCanvas) {
      this.bugStatusChart = new Chart(staCanvas, {
        type: 'bar',
        data: {
          labels: ['Open', 'In Progress', 'Resolved', 'Closed', "Won't Fix"],
          datasets: [{
            data: [
              data.bug_status.open,
              data.bug_status.in_progress,
              data.bug_status.resolved,
              data.bug_status.closed,
              data.bug_status.wont_fix,
            ],
            backgroundColor: ['#ef4444', '#f59e0b', '#22c55e', '#64748b', '#94a3b8'],
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          indexAxis: 'y',
          plugins: { legend: { display: false } },
          scales: { x: { beginAtZero: true, ticks: { stepSize: 1 } } },
        },
      });
    }

    // ── Requirement coverage doughnut ─────────────────────────────────────────
    const covCanvas = this.getCanvas('coverageChart');
    if (covCanvas) {
      this.coverageChart = new Chart(covCanvas, {
        type: 'doughnut',
        data: {
          labels: ['Covered', 'Uncovered'],
          datasets: [{
            data: [
              data.requirement_coverage.covered,
              data.requirement_coverage.uncovered,
            ],
            backgroundColor: ['#3b82f6', '#e2e8f0'],
            hoverOffset: 4,
          }],
        },
        options: {
          responsive: true,
          maintainAspectRatio: false,
          cutout: '72%',
          plugins: {
            legend: { display: false },
            tooltip: {
              callbacks: {
                label: (context) => ` ${context.label}: ${context.raw} requirement(s)`
              }
            }
          },
        },
      });
    }

    this.chartsReady = true;
  }

  getHealthColor(): string {
    const score = this.analytics?.summary.health_score ?? 0;
    if (score >= 80) return 'health-good';
    if (score >= 50) return 'health-warn';
    return 'health-bad';
  }

  exportCsv(type: 'runs' | 'bugs'): void {
    if (!this.selectedProjectId) return;
    this.exportMenuOpen = false;
    this.analyticsService.exportCsv(this.selectedProjectId, type).subscribe({
      next: (blob) => {
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = type === 'runs' ? 'qa-report-runs.csv' : 'qa-report-bugs.csv';
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
      },
      error: () => {
        this.errorMessage = 'Failed to export CSV. Please try again.';
      },
    });
  }

  toggleExportMenu(): void {
    this.exportMenuOpen = !this.exportMenuOpen;
  }
}
