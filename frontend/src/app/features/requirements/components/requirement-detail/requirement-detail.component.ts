import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  MAT_DIALOG_DATA,
  MatDialog,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import {
  Requirement,
  RequirementService,
} from '../../../../core/services/requirement.service';
import { RequirementDialogComponent } from '../requirement-dialog/requirement-dialog.component';

export interface RequirementDetailData {
  projectId: string;
  requirement: Requirement;
}

@Component({
  selector: 'app-requirement-detail',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule, MatIconModule],
  templateUrl: './requirement-detail.component.html',
  styleUrl: './requirement-detail.component.scss',
})
export class RequirementDetailComponent {
  req: Requirement;
  isDeleting = false;

  constructor(
    private reqService: RequirementService,
    private dialog: MatDialog,
    public dialogRef: MatDialogRef<RequirementDetailComponent>,
    @Inject(MAT_DIALOG_DATA) public data: RequirementDetailData
  ) {
    this.req = data.requirement;
  }

  onEdit(): void {
    const editRef = this.dialog.open(RequirementDialogComponent, {
      width: '560px',
      data: {
        projectId: this.data.projectId,
        requirement: this.req,
      },
    });

    editRef.afterClosed().subscribe((updated: Requirement | undefined) => {
      if (updated) {
        this.req = updated;
        this.dialogRef.close({ action: 'updated', requirement: updated });
      }
    });
  }

  onDelete(): void {
    if (!confirm(`Are you sure you want to delete ${this.req.req_key}? This cannot be undone.`)) {
      return;
    }

    this.isDeleting = true;
    this.reqService.deleteRequirement(this.data.projectId, this.req.id).subscribe({
      next: () => {
        this.isDeleting = false;
        this.dialogRef.close({ action: 'deleted', requirementId: this.req.id });
      },
      error: (err) => {
        this.isDeleting = false;
        alert(err.error?.detail || 'Failed to delete requirement.');
      },
    });
  }

  onClose(): void {
    this.dialogRef.close();
  }

  getPriorityClass(priority: string): string {
    switch (priority) {
      case 'critical':
        return 'bg-purple-100 text-purple-700 border-purple-200';
      case 'high':
        return 'bg-red-100 text-red-700 border-red-200';
      case 'medium':
        return 'bg-amber-100 text-amber-700 border-amber-200';
      case 'low':
        return 'bg-green-100 text-green-700 border-green-200';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  }

  getCategoryLabel(category: string): string {
    switch (category) {
      case 'ui_ux':
        return 'UI / UX';
      case 'non_functional':
        return 'Non-Functional';
      default:
        return category.charAt(0).toUpperCase() + category.slice(1);
    }
  }
}
