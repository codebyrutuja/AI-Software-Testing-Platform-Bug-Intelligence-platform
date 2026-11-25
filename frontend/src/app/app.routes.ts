import { Routes } from '@angular/router';
import { authGuard } from './core/guards/auth.guard';
import { ShellComponent } from './layout/shell/shell.component';

export const routes: Routes = [
  // ── Public Routes (no auth required) ──────────────────────────────────────
  {
    path: 'login',
    loadComponent: () =>
      import('./features/auth/login/login.component').then(
        (m) => m.LoginComponent
      ),
  },
  {
    path: 'register',
    loadComponent: () =>
      import('./features/auth/register/register.component').then(
        (m) => m.RegisterComponent
      ),
  },

  // ── Protected Shell & Child Routes ─────────────────────────────────────────
  {
    path: '',
    component: ShellComponent,
    canActivate: [authGuard],
    children: [
      {
        path: 'dashboard',
        loadComponent: () =>
          import('./features/dashboard/dashboard.component').then(
            (m) => m.DashboardComponent
          ),
      },
      {
        path: 'projects',
        loadComponent: () =>
          import('./features/projects/projects.component').then(
            (m) => m.ProjectsComponent
          ),
      },
      {
        path: 'requirements',
        loadComponent: () =>
          import('./features/requirements/requirements.component').then(
            (m) => m.RequirementsComponent
          ),
      },
      {
        path: 'test-cases',
        loadComponent: () =>
          import('./features/test-cases/test-cases.component').then(
            (m) => m.TestCasesComponent
          ),
      },
      {
        path: 'test-runs',
        loadComponent: () =>
          import('./features/test-runs/test-runs.component').then(
            (m) => m.TestRunsComponent
          ),
      },
      {
        path: 'test-runs/:projectId/:runId/execute',
        loadComponent: () =>
          import(
            './features/test-runs/components/run-execution/run-execution.component'
          ).then((m) => m.RunExecutionComponent),
      },
      {
        path: 'bugs',
        loadComponent: () =>
          import('./features/bug-tracker/bug-tracker.component').then(
            (m) => m.BugTrackerComponent
          ),
      },
      {
        path: '',
        redirectTo: 'projects',
        pathMatch: 'full',
      },
    ],
  },

  // ── Fallback Redirect ───────────────────────────────────────────────────────
  { path: '**', redirectTo: '/login' },
];
