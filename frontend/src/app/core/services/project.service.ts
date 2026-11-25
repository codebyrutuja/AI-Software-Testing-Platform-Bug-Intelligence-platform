import { Injectable } from '@angular/core';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Observable } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface Project {
  id: string;
  organization_id: string;
  name: string;
  key: string;
  description: string | null;
  status: 'active' | 'archived';
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface CreateProjectRequest {
  name: string;
  key: string;
  description?: string;
}

export interface UpdateProjectRequest {
  name?: string;
  description?: string;
  status?: 'active' | 'archived';
}

@Injectable({ providedIn: 'root' })
export class ProjectService {
  private readonly apiUrl = environment.apiUrl;

  constructor(private http: HttpClient) {}

  getProjects(orgId: string, skip = 0, limit = 50): Observable<Project[]> {
    const params = new HttpParams().set('skip', skip).set('limit', limit);
    return this.http.get<Project[]>(
      `${this.apiUrl}/organizations/${orgId}/projects`,
      { params }
    );
  }

  createProject(orgId: string, data: CreateProjectRequest): Observable<Project> {
    return this.http.post<Project>(
      `${this.apiUrl}/organizations/${orgId}/projects`,
      data
    );
  }

  getProject(projectId: string): Observable<Project> {
    return this.http.get<Project>(`${this.apiUrl}/projects/${projectId}`);
  }

  updateProject(projectId: string, data: UpdateProjectRequest): Observable<Project> {
    return this.http.patch<Project>(`${this.apiUrl}/projects/${projectId}`, data);
  }

  archiveProject(projectId: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/projects/${projectId}`);
  }
}
