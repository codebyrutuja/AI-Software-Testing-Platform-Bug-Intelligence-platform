import { inject } from '@angular/core';
import { CanActivateFn, Router } from '@angular/router';
import { AuthService } from '../services/auth.service';

/**
 * AUTH GUARD
 * ───────────
 * Protects routes that require authentication.
 * If the user is not logged in, they are redirected to /login.
 *
 * WHY A GUARD?
 *   Without guards, unauthenticated users could navigate directly to
 *   /dashboard, /bugs, etc. by typing the URL.
 *   The guard intercepts navigation before the component loads.
 *
 * Angular 17 uses functional guards (CanActivateFn) instead of class-based.
 *
 * Usage in routes:
 *   { path: 'dashboard', component: DashboardComponent, canActivate: [authGuard] }
 */
export const authGuard: CanActivateFn = (_route, _state) => {
  const authService = inject(AuthService);
  const router = inject(Router);

  if (authService.isAuthenticated()) {
    return true; // User has a token — allow navigation
  }

  // No token — redirect to login
  // `state.url` is the URL the user tried to access; we could pass it
  // as a query param so after login we redirect them back (future enhancement).
  router.navigate(['/login']);
  return false;
};
