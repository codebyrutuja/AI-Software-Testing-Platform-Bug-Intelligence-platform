import { Component, OnDestroy, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Subscription } from 'rxjs';

import {
  Organization,
  OrganizationService,
} from '../../core/services/organization.service';
import { Project, ProjectService } from '../../core/services/project.service';
import { ProjectCardComponent } from './project-card/project-card.component';
import { ProjectDialogComponent } from './project-dialog/project-dialog.component';

@Component({
  selector: 'app-projects',
  standalone: true,
  imports: [
    CommonModule,
    MatButtonModule,
    MatIconModule,
    MatDialogModule,
    MatProgressSpinnerModule,
    ProjectCardComponent,
  ],
  templateUrl: './projects.component.html',
  styleUrl: './projects.component.scss',
})
export class ProjectsComponent implements OnInit, OnDestroy {
  activeOrg: Organization | null = null;
  projects: Project[] = [];
  isLoading = false;
  errorMessage = '';

  private sub = new Subscription();

  constructor(
    private orgService: OrganizationService,
    private projectService: ProjectService,
    private dialog: MatDialog
  ) {}

  ngOnInit(): void {
    this.sub.add(
      this.orgService.activeOrg$.subscribe((org) => {
        this.activeOrg = org;
        if (org) {
          this.loadProjects(org.id);
        } else {
          this.projects = [];
        }
      })
    );
  }

  ngOnDestroy(): void {
    this.sub.unsubscribe();
  }

  loadProjects(orgId: string): void {
    this.isLoading = true;
    this.errorMessage = '';

    this.projectService.getProjects(orgId).subscribe({
      next: (data) => {
        this.projects = data;
        this.isLoading = false;
      },
      error: (err) => {
        this.errorMessage = err.error?.detail || 'Failed to load projects.';
        this.isLoading = false;
      },
    });
  }

  openCreateProjectDialog(): void {
    if (!this.activeOrg) {
      alert('Please select or create an organization first.');
      return;
    }

    const dialogRef = this.dialog.open(ProjectDialogComponent, {
      width: '480px',
      data: { orgId: this.activeOrg.id },
    });

    dialogRef.afterClosed().subscribe((result: Project | undefined) => {
      if (result) {
        // Prepend new project to list instantly without reload
        this.projects = [result, ...this.projects];
      }
    });
  }

  onDeleteProject(project: Project): void {
    if (confirm(`Are you sure you want to archive project "${project.name}"?`)) {
      this.projectService.archiveProject(project.id).subscribe({
        next: () => {
          this.projects = this.projects.filter((p) => p.id !== project.id);
        },
        error: (err) => {
          this.errorMessage = err.error?.detail || 'Failed to archive project.';
        },
      });
    }
  }
}
