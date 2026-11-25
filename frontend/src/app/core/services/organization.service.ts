import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { environment } from '../../../environments/environment';

export interface Organization {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  is_active: boolean;
  created_by: string | null;
  created_at: string;
  updated_at: string;
}

export interface Member {
  id: string;
  organization_id: string;
  user_id: string;
  role: 'owner' | 'admin' | 'member' | 'viewer';
  joined_at: string;
  user?: {
    id: string;
    email: string;
    full_name: string | null;
  };
}

export interface CreateOrganizationRequest {
  name: string;
  description?: string;
}

export interface AddMemberRequest {
  email: string;
  role: 'owner' | 'admin' | 'member' | 'viewer';
}

const ACTIVE_ORG_KEY = 'active_organization';

@Injectable({ providedIn: 'root' })
export class OrganizationService {
  private readonly apiUrl = `${environment.apiUrl}/organizations`;

  private activeOrgSubject = new BehaviorSubject<Organization | null>(null);
  public activeOrg$ = this.activeOrgSubject.asObservable();

  constructor(private http: HttpClient) {
    this.loadSavedActiveOrg();
  }

  // ── Active Organization State ───────────────────────────────────────────────

  getActiveOrg(): Organization | null {
    return this.activeOrgSubject.getValue();
  }

  setActiveOrg(org: Organization): void {
    localStorage.setItem(ACTIVE_ORG_KEY, JSON.stringify(org));
    this.activeOrgSubject.next(org);
  }

  private loadSavedActiveOrg(): void {
    const saved = localStorage.getItem(ACTIVE_ORG_KEY);
    if (saved) {
      try {
        const org: Organization = JSON.parse(saved);
        this.activeOrgSubject.next(org);
      } catch {
        localStorage.removeItem(ACTIVE_ORG_KEY);
      }
    }
  }

  // ── API Calls ───────────────────────────────────────────────────────────────

  getMyOrganizations(): Observable<Organization[]> {
    return this.http.get<Organization[]>(`${this.apiUrl}/`).pipe(
      tap((orgs) => {
        // If there's no active org selected, pick the first one automatically
        if (orgs.length > 0 && !this.getActiveOrg()) {
          this.setActiveOrg(orgs[0]);
        }
      })
    );
  }

  createOrganization(data: CreateOrganizationRequest): Observable<Organization> {
    return this.http.post<Organization>(`${this.apiUrl}/`, data).pipe(
      tap((newOrg) => {
        // Automatically make newly created org the active one
        this.setActiveOrg(newOrg);
      })
    );
  }

  getOrganization(orgId: string): Observable<Organization> {
    return this.http.get<Organization>(`${this.apiUrl}/${orgId}`);
  }

  getMembers(orgId: string): Observable<Member[]> {
    return this.http.get<Member[]>(`${this.apiUrl}/${orgId}/members`);
  }

  addMember(orgId: string, data: AddMemberRequest): Observable<Member> {
    return this.http.post<Member>(`${this.apiUrl}/${orgId}/members`, data);
  }

  removeMember(orgId: string, userId: string): Observable<void> {
    return this.http.delete<void>(`${this.apiUrl}/${orgId}/members/${userId}`);
  }
}
