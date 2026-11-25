import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface TestStep {
  id: string;
  test_case_id: string;
  step_number: number;
  action: string;
  test_data?: string | null;
  expected_result: string;
  created_at: string;
}

export interface TestSuite {
  id: string;
  project_id: string;
  parent_suite_id: string | null;
  name: string;
  description: string | null;
  created_at: string;
  case_count: number;
}

export interface TestCase {
  id: string;
  project_id: string;
  suite_id: string | null;
  suite_name?: string | null;
  requirement_id: string | null;
  requirement_key?: string | null;
  requirement_title?: string | null;
  tc_key: string;
  title: string;
  description: string | null;
  preconditions: string | null;
  test_type: 'manual' | 'automated' | 'regression' | 'smoke' | 'sanity';
  priority: 'low' | 'medium' | 'high' | 'critical';
  status: 'draft' | 'active' | 'deprecated';
  estimated_duration_minutes: number;
  created_by: string | null;
  created_at: string;
  updated_at: string;
  steps: TestStep[];
}

export interface TestCaseListResponse {
  items: TestCase[];
  total: number;
  skip: number;
  limit: number;
}

export interface CreateTestSuiteRequest {
  name: string;
  description?: string;
  parent_suite_id?: string;
}

export interface UpdateTestSuiteRequest {
  name?: string;
  description?: string;
  parent_suite_id?: string;
}

export interface CreateTestStepPayload {
  step_number: number;
  action: string;
  test_data?: string;
  expected_result: string;
}

export interface CreateTestCaseRequest {
  title: string;
  suite_id?: string;
  requirement_id?: string;
  description?: string;
  preconditions?: string;
  test_type?: string;
  priority?: string;
  status?: string;
  estimated_duration_minutes?: number;
  steps?: CreateTestStepPayload[];
}

export interface UpdateTestCaseRequest {
  title?: string;
  suite_id?: string;
  requirement_id?: string;
  description?: string;
  preconditions?: string;
  test_type?: string;
  priority?: string;
  status?: string;
  estimated_duration_minutes?: number;
  steps?: CreateTestStepPayload[];
}

export interface TestCaseFilters {
  suite_id?: string;
  requirement_id?: string;
  test_type?: string;
  priority?: string;
  status?: string;
  search?: string;
  skip?: number;
  limit?: number;
}

@Injectable({ providedIn: 'root' })
export class TestCaseService {
  private readonly apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  // ── Test Suites ─────────────────────────────────────────────────────────────

  getSuites(projectId: string): Observable<TestSuite[]> {
    return this.http.get<TestSuite[]>(
      `${this.apiUrl}/projects/${projectId}/suites`
    );
  }

  createSuite(
    projectId: string,
    data: CreateTestSuiteRequest
  ): Observable<TestSuite> {
    return this.http.post<TestSuite>(
      `${this.apiUrl}/projects/${projectId}/suites`,
      data
    );
  }

  updateSuite(
    projectId: string,
    suiteId: string,
    data: UpdateTestSuiteRequest
  ): Observable<TestSuite> {
    return this.http.put<TestSuite>(
      `${this.apiUrl}/projects/${projectId}/suites/${suiteId}`,
      data
    );
  }

  deleteSuite(projectId: string, suiteId: string): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(
      `${this.apiUrl}/projects/${projectId}/suites/${suiteId}`
    );
  }

  // ── Test Cases ──────────────────────────────────────────────────────────────

  getTestCases(
    projectId: string,
    filters?: TestCaseFilters
  ): Observable<TestCaseListResponse> {
    let params = new HttpParams();
    if (filters) {
      if (filters.suite_id) params = params.set('suite_id', filters.suite_id);
      if (filters.requirement_id) params = params.set('requirement_id', filters.requirement_id);
      if (filters.test_type) params = params.set('test_type', filters.test_type);
      if (filters.priority) params = params.set('priority', filters.priority);
      if (filters.status) params = params.set('status', filters.status);
      if (filters.search) params = params.set('search', filters.search);
      if (filters.skip !== undefined) params = params.set('skip', filters.skip);
      if (filters.limit !== undefined) params = params.set('limit', filters.limit);
    }

    return this.http.get<TestCaseListResponse>(
      `${this.apiUrl}/projects/${projectId}/test-cases`,
      { params }
    );
  }

  getTestCase(projectId: string, caseId: string): Observable<TestCase> {
    return this.http.get<TestCase>(
      `${this.apiUrl}/projects/${projectId}/test-cases/${caseId}`
    );
  }

  createTestCase(
    projectId: string,
    data: CreateTestCaseRequest
  ): Observable<TestCase> {
    return this.http.post<TestCase>(
      `${this.apiUrl}/projects/${projectId}/test-cases`,
      data
    );
  }

  updateTestCase(
    projectId: string,
    caseId: string,
    data: UpdateTestCaseRequest
  ): Observable<TestCase> {
    return this.http.put<TestCase>(
      `${this.apiUrl}/projects/${projectId}/test-cases/${caseId}`,
      data
    );
  }

  deleteTestCase(
    projectId: string,
    caseId: string
  ): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(
      `${this.apiUrl}/projects/${projectId}/test-cases/${caseId}`
    );
  }
}
