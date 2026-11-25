import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

// ── Response shapes ──────────────────────────────────────────────────────────

export interface RunPassFailBar {
  run_key: string;
  run_name: string;
  status: string;
  environment: string;
  passed_count: number;
  failed_count: number;
  blocked_count: number;
  skipped_count: number;
  not_run_count: number;
  total_count: number;
  pass_rate: number;
}

export interface BugSeverityBreakdown {
  critical: number;
  high: number;
  medium: number;
  low: number;
}

export interface BugStatusBreakdown {
  open: number;
  in_progress: number;
  resolved: number;
  closed: number;
  wont_fix: number;
}

export interface UncoveredRequirement {
  req_key: string;
  title: string;
  priority: string;
  status: string;
}

export interface RequirementCoverage {
  covered: number;
  uncovered: number;
  coverage_percentage: number;
  uncovered_requirements: UncoveredRequirement[];
}

export interface ProjectSummary {
  total_requirements: number;
  total_test_cases: number;
  total_test_runs: number;
  total_bugs: number;
  health_score: number;
}

export interface AnalyticsDashboardResponse {
  summary: ProjectSummary;
  run_history: RunPassFailBar[];
  bug_severity: BugSeverityBreakdown;
  bug_status: BugStatusBreakdown;
  requirement_coverage: RequirementCoverage;
}

// ── Service ───────────────────────────────────────────────────────────────────

@Injectable({ providedIn: 'root' })
export class AnalyticsService {
  private readonly base = `${environment.apiUrl}/analytics`;

  constructor(private http: HttpClient) {}

  getDashboard(projectId: string): Observable<AnalyticsDashboardResponse> {
    return this.http.get<AnalyticsDashboardResponse>(
      `${this.base}/dashboard?project_id=${projectId}`
    );
  }

  exportCsv(projectId: string, type: 'runs' | 'bugs'): Observable<Blob> {
    return this.http.get(
      `${this.base}/export/csv?project_id=${projectId}&type=${type}`,
      { responseType: 'blob' }
    );
  }
}
