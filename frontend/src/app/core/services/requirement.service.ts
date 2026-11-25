import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface AcceptanceCriteria {
  id: string;
  requirement_id: string;
  criteria: string;
  order_index: number;
  created_at: string;
}

export interface Requirement {
  id: string;
  project_id: string;
  document_id: string | null;
  req_key: string;
  title: string;
  description: string | null;
  category: 'functional' | 'non_functional' | 'security' | 'ui_ux' | 'performance';
  priority: 'low' | 'medium' | 'high' | 'critical';
  status: 'draft' | 'approved' | 'deprecated';
  created_by: string | null;
  created_at: string;
  updated_at: string;
  acceptance_criteria: AcceptanceCriteria[];
}

export interface RequirementListResponse {
  items: Requirement[];
  total: number;
  skip: number;
  limit: number;
}

export interface RequirementDocument {
  id: string;
  project_id: string;
  uploaded_by: string | null;
  filename: string;
  file_type: string;
  file_size_bytes: number;
  parsing_status: 'pending' | 'parsed' | 'failed';
  created_at: string;
  requirements_count?: number;
}

export interface DocumentUploadResponse {
  document: RequirementDocument;
  extracted_count: number;
  requirements: Requirement[];
}

export interface CreateRequirementRequest {
  title: string;
  description?: string;
  category?: string;
  priority?: string;
  status?: string;
  acceptance_criteria?: string[];
}

export interface UpdateRequirementRequest {
  title?: string;
  description?: string;
  category?: string;
  priority?: string;
  status?: string;
  acceptance_criteria?: string[];
}

export interface RequirementFilters {
  category?: string;
  priority?: string;
  status?: string;
  search?: string;
  skip?: number;
  limit?: number;
}

@Injectable({ providedIn: 'root' })
export class RequirementService {
  private readonly apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  listRequirements(
    projectId: string,
    filters?: RequirementFilters
  ): Observable<RequirementListResponse> {
    let params = new HttpParams();
    if (filters) {
      if (filters.category) params = params.set('category', filters.category);
      if (filters.priority) params = params.set('priority', filters.priority);
      if (filters.status) params = params.set('status', filters.status);
      if (filters.search) params = params.set('search', filters.search);
      if (filters.skip !== undefined) params = params.set('skip', filters.skip);
      if (filters.limit !== undefined) params = params.set('limit', filters.limit);
    }
    return this.http.get<RequirementListResponse>(
      `${this.apiUrl}/projects/${projectId}/requirements`,
      { params }
    );
  }

  getRequirement(projectId: string, requirementId: string): Observable<Requirement> {
    return this.http.get<Requirement>(
      `${this.apiUrl}/projects/${projectId}/requirements/${requirementId}`
    );
  }

  createRequirement(
    projectId: string,
    data: CreateRequirementRequest
  ): Observable<Requirement> {
    return this.http.post<Requirement>(
      `${this.apiUrl}/projects/${projectId}/requirements`,
      data
    );
  }

  updateRequirement(
    projectId: string,
    requirementId: string,
    data: UpdateRequirementRequest
  ): Observable<Requirement> {
    return this.http.put<Requirement>(
      `${this.apiUrl}/projects/${projectId}/requirements/${requirementId}`,
      data
    );
  }

  deleteRequirement(projectId: string, requirementId: string): Observable<{ message: string }> {
    return this.http.delete<{ message: string }>(
      `${this.apiUrl}/projects/${projectId}/requirements/${requirementId}`
    );
  }

  uploadDocument(projectId: string, file: File): Observable<DocumentUploadResponse> {
    const formData = new FormData();
    formData.append('file', file, file.name);
    return this.http.post<DocumentUploadResponse>(
      `${this.apiUrl}/projects/${projectId}/requirements/upload`,
      formData
    );
  }

  listDocuments(projectId: string): Observable<RequirementDocument[]> {
    return this.http.get<RequirementDocument[]>(
      `${this.apiUrl}/projects/${projectId}/documents`
    );
  }
}
