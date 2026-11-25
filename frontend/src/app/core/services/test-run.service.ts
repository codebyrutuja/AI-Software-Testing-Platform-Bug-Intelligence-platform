import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface TestRunItem {
  id: string;
  test_run_id: string;
  test_case_id: string | null;
  tc_key: string | null;
  tc_title: string | null;
  result: 'not_run' | 'passed' | 'failed' | 'blocked' | 'skipped';
  failure_notes: string | null;
  actual_duration_minutes: number | null;
  executed_by: string | null;
  executed_at: string | null;
  created_at: string;
}

export interface TestRun {
  id: string;
  project_id: string;
  run_key: string;
  name: string;
  description: string | null;
  status: 'planned' | 'in_progress' | 'completed' | 'aborted';
  environment: 'local' | 'staging' | 'qa' | 'production';
  created_by: string | null;
  started_at: string | null;
  completed_at: string | null;
  created_at: string;
  updated_at: string;
  total_count: number;
  passed_count: number;
  failed_count: number;
  blocked_count: number;
  skipped_count: number;
  not_run_count: number;
  items: TestRunItem[];
}

export interface TestRunListResponse {
  items: TestRun[];
  total: number;
  skip: number;
  limit: number;
}

export interface CreateTestRunRequest {
  name: string;
  description?: string;
  environment: string;
  test_case_ids: string[];
}

export interface UpdateTestRunRequest {
  name?: string;
  description?: string;
  status?: string;
  environment?: string;
}

export interface SubmitItemResultRequest {
  result: 'passed' | 'failed' | 'blocked' | 'skipped';
  failure_notes?: string;
  actual_duration_minutes?: number;
}

@Injectable({ providedIn: 'root' })
export class TestRunService {
  private readonly apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getRuns(
    projectId: string,
    statusFilter?: string,
    skip = 0,
    limit = 50
  ): Observable<TestRunListResponse> {
    let params = new HttpParams().set('skip', skip).set('limit', limit);
    if (statusFilter) {
      params = params.set('status', statusFilter);
    }
    return this.http.get<TestRunListResponse>(
      `${this.apiUrl}/projects/${projectId}/runs`,
      { params }
    );
  }

  getRun(projectId: string, runId: string): Observable<TestRun> {
    return this.http.get<TestRun>(
      `${this.apiUrl}/projects/${projectId}/runs/${runId}`
    );
  }

  createRun(
    projectId: string,
    data: CreateTestRunRequest
  ): Observable<TestRun> {
    return this.http.post<TestRun>(
      `${this.apiUrl}/projects/${projectId}/runs`,
      data
    );
  }

  updateRun(
    projectId: string,
    runId: string,
    data: UpdateTestRunRequest
  ): Observable<TestRun> {
    return this.http.put<TestRun>(
      `${this.apiUrl}/projects/${projectId}/runs/${runId}`,
      data
    );
  }

  deleteRun(projectId: string, runId: string): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(
      `${this.apiUrl}/projects/${projectId}/runs/${runId}`
    );
  }

  submitItemResult(
    projectId: string,
    runId: string,
    itemId: string,
    data: SubmitItemResultRequest
  ): Observable<TestRunItem> {
    return this.http.put<TestRunItem>(
      `${this.apiUrl}/projects/${projectId}/runs/${runId}/items/${itemId}/result`,
      data
    );
  }
}
