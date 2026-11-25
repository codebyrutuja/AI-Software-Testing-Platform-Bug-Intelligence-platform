import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface Bug {
  id: string;
  project_id: string;
  bug_key: string;
  title: string;
  description: string | null;
  steps_to_reproduce: string | null;
  expected_behavior: string | null;
  actual_behavior: string | null;
  severity: 'critical' | 'high' | 'medium' | 'low';
  priority: 'critical' | 'high' | 'medium' | 'low';
  status: 'open' | 'in_progress' | 'resolved' | 'closed' | 'wont_fix';
  environment: string | null;
  browser_os: string | null;
  test_run_item_id: string | null;
  test_case_id: string | null;
  tc_key: string | null;
  tc_title: string | null;
  requirement_id: string | null;
  requirement_key: string | null;
  requirement_title: string | null;
  reported_by: string | null;
  reporter_name: string | null;
  assigned_to: string | null;
  assignee_name: string | null;
  reported_at: string;
  resolved_at: string | null;
  created_at: string;
  updated_at: string;
}

export interface BugListResponse {
  items: Bug[];
  total: number;
  skip: number;
  limit: number;
}

export interface BugStatsResponse {
  total: number;
  open: number;
  in_progress: number;
  resolved: number;
  closed: number;
  wont_fix: number;
  by_severity: { [key: string]: number };
}

export interface CreateBugRequest {
  title: string;
  description?: string;
  steps_to_reproduce?: string;
  expected_behavior?: string;
  actual_behavior?: string;
  severity?: string;
  priority?: string;
  environment?: string;
  browser_os?: string;
  test_case_id?: string;
  requirement_id?: string;
  test_run_item_id?: string;
  assigned_to?: string;
}

export interface UpdateBugRequest {
  title?: string;
  description?: string;
  steps_to_reproduce?: string;
  expected_behavior?: string;
  actual_behavior?: string;
  severity?: string;
  priority?: string;
  status?: string;
  environment?: string;
  browser_os?: string;
  assigned_to?: string;
}

export interface BugFilters {
  status?: string;
  severity?: string;
  priority?: string;
  assigned_to?: string;
  search?: string;
  skip?: number;
  limit?: number;
}

@Injectable({ providedIn: 'root' })
export class BugService {
  private readonly apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getBugs(projectId: string, filters?: BugFilters): Observable<BugListResponse> {
    let params = new HttpParams();
    if (filters) {
      if (filters.status) params = params.set('status', filters.status);
      if (filters.severity) params = params.set('severity', filters.severity);
      if (filters.priority) params = params.set('priority', filters.priority);
      if (filters.assigned_to) params = params.set('assigned_to', filters.assigned_to);
      if (filters.search) params = params.set('search', filters.search);
      if (filters.skip !== undefined) params = params.set('skip', filters.skip);
      if (filters.limit !== undefined) params = params.set('limit', filters.limit);
    }
    return this.http.get<BugListResponse>(
      `${this.apiUrl}/projects/${projectId}/bugs`,
      { params }
    );
  }

  getBug(projectId: string, bugId: string): Observable<Bug> {
    return this.http.get<Bug>(`${this.apiUrl}/projects/${projectId}/bugs/${bugId}`);
  }

  getStats(projectId: string): Observable<BugStatsResponse> {
    return this.http.get<BugStatsResponse>(
      `${this.apiUrl}/projects/${projectId}/bugs/stats`
    );
  }

  createBug(projectId: string, data: CreateBugRequest): Observable<Bug> {
    return this.http.post<Bug>(
      `${this.apiUrl}/projects/${projectId}/bugs`,
      data
    );
  }

  updateBug(
    projectId: string,
    bugId: string,
    data: UpdateBugRequest
  ): Observable<Bug> {
    return this.http.put<Bug>(
      `${this.apiUrl}/projects/${projectId}/bugs/${bugId}`,
      data
    );
  }

  deleteBug(projectId: string, bugId: string): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(
      `${this.apiUrl}/projects/${projectId}/bugs/${bugId}`
    );
  }

  quickReportFromRunItem(
    projectId: string,
    runId: string,
    itemId: string,
    data: CreateBugRequest
  ): Observable<Bug> {
    return this.http.post<Bug>(
      `${this.apiUrl}/projects/${projectId}/runs/${runId}/items/${itemId}/report-bug`,
      data
    );
  }
}
