import {
  HttpEvent,
  HttpHandlerFn,
  HttpInterceptorFn,
  HttpRequest,
  HttpErrorResponse,
} from '@angular/common/http';
import { inject } from '@angular/core';
import { Observable, throwError, catchError, switchMap } from 'rxjs';
import { AuthService } from '../services/auth.service';

/**
 * AUTH INTERCEPTOR
 * ─────────────────
 * Automatically attaches the JWT token to every outgoing HTTP request.
 * Also handles token refresh when a 401 (Unauthorized) response is received.
 *
 * WHY AN INTERCEPTOR?
 *   Without this, every service would need to manually add:
 *     headers: { Authorization: `Bearer ${token}` }
 *   The interceptor does it once, automatically, for ALL requests.
 *
 * Angular 17 uses functional interceptors (HttpInterceptorFn) instead of class-based.
 */
export const authInterceptor: HttpInterceptorFn = (
  req: HttpRequest<unknown>,
  next: HttpHandlerFn
): Observable<HttpEvent<unknown>> => {
  const authService = inject(AuthService);

  // ── Attach Token ────────────────────────────────────────────────────────────
  const token = authService.getAccessToken();

  // Clone the request and add the Authorization header.
  // We MUST clone (HTTP requests are immutable in Angular).
  const authenticatedReq = token
    ? req.clone({
        headers: req.headers.set('Authorization', `Bearer ${token}`),
      })
    : req;

  // ── Handle Response ─────────────────────────────────────────────────────────
  return next(authenticatedReq).pipe(
    catchError((error: HttpErrorResponse) => {
      // If we get a 401, our access token has expired.
      // Try to refresh it using the refresh token.
      if (error.status === 401 && authService.getRefreshToken()) {
        return authService.refreshToken().pipe(
          switchMap(() => {
            // Retry the original request with the new access token
            const newToken = authService.getAccessToken();
            const retryReq = newToken
              ? req.clone({
                  headers: req.headers.set('Authorization', `Bearer ${newToken}`),
                })
              : req;
            return next(retryReq);
          }),
          catchError((refreshError) => {
            // Refresh also failed — session is truly expired, force logout
            authService.logout();
            return throwError(() => refreshError);
          })
        );
      }

      // For all other errors, pass through unchanged
      return throwError(() => error);
    })
  );
};
