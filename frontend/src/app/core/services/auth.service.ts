import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Router } from '@angular/router';
import { BehaviorSubject, Observable, tap } from 'rxjs';
import { environment } from '../../../environments/environment';

// ── Interfaces ────────────────────────────────────────────────────────────────
// Match exactly the JSON shapes returned by the backend Pydantic schemas

export interface User {
  id: string;
  email: string;
  full_name: string | null;
  role: 'superadmin' | 'admin' | 'member' | 'viewer';
  is_active: boolean;
  is_superadmin: boolean;
  created_at: string;
  updated_at: string;
  last_login_at: string | null;
}

export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export interface LoginRequest {
  email: string;
  password: string;
}

export interface RegisterRequest {
  email: string;
  password: string;
  full_name?: string;
}

// ── Storage Keys ──────────────────────────────────────────────────────────────
const ACCESS_TOKEN_KEY  = 'access_token';
const REFRESH_TOKEN_KEY = 'refresh_token';

@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly apiUrl = environment.apiUrl;

  /**
   * BehaviorSubject holds the current user in memory.
   * Components subscribe to currentUser$ to react to login/logout.
   * BehaviorSubject (vs Subject) replays the last value to new subscribers.
   */
  private currentUserSubject = new BehaviorSubject<User | null>(null);
  currentUser$ = this.currentUserSubject.asObservable();

  constructor(private http: HttpClient, private router: Router) {
    // On app startup, if a token is stored, load the user profile
    if (this.getAccessToken()) {
      this.loadCurrentUser().subscribe({
        error: () => this.clearTokens(), // Token may be expired — clear it
      });
    }
  }

  // ── Token Storage ───────────────────────────────────────────────────────────

  getAccessToken(): string | null {
    return localStorage.getItem(ACCESS_TOKEN_KEY);
  }

  getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_TOKEN_KEY);
  }

  private storeTokens(tokens: TokenResponse): void {
    localStorage.setItem(ACCESS_TOKEN_KEY, tokens.access_token);
    localStorage.setItem(REFRESH_TOKEN_KEY, tokens.refresh_token);
  }

  private clearTokens(): void {
    localStorage.removeItem(ACCESS_TOKEN_KEY);
    localStorage.removeItem(REFRESH_TOKEN_KEY);
    this.currentUserSubject.next(null);
  }

  // ── Auth State ──────────────────────────────────────────────────────────────

  isAuthenticated(): boolean {
    return !!this.getAccessToken();
  }

  getCurrentUserValue(): User | null {
    return this.currentUserSubject.getValue();
  }

  // ── API Calls ───────────────────────────────────────────────────────────────

  login(credentials: LoginRequest): Observable<TokenResponse> {
    return this.http
      .post<TokenResponse>(`${this.apiUrl}/auth/login`, credentials)
      .pipe(
        tap((tokens) => {
          this.storeTokens(tokens);
          // After storing tokens, fetch the user profile
          this.loadCurrentUser().subscribe();
        })
      );
  }

  register(data: RegisterRequest): Observable<User> {
    return this.http.post<User>(`${this.apiUrl}/auth/register`, data);
  }

  logout(): void {
    // Notify backend (best effort — don't block UI on failure)
    if (this.getAccessToken()) {
      this.http.post(`${this.apiUrl}/auth/logout`, {}).subscribe({
        error: () => {}, // Ignore errors — we clear locally regardless
      });
    }
    this.clearTokens();
    this.router.navigate(['/login']);
  }

  refreshToken(): Observable<TokenResponse> {
    const refreshToken = this.getRefreshToken();
    return this.http
      .post<TokenResponse>(`${this.apiUrl}/auth/refresh`, {
        refresh_token: refreshToken,
      })
      .pipe(
        tap((tokens) => {
          this.storeTokens(tokens);
        })
      );
  }

  loadCurrentUser(): Observable<User> {
    return this.http.get<User>(`${this.apiUrl}/auth/me`).pipe(
      tap((user) => {
        this.currentUserSubject.next(user);
      })
    );
  }
}
