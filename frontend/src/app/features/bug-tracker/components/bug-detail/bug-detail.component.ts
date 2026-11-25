import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { Bug, BugService, UpdateBugRequest } from '../../../../core/services/bug.service';

export interface BugDetailData {
  bug: Bug;
}

@Component({
  selector: 'app-bug-detail',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './bug-detail.component.html',
  styleUrl: './bug-detail.component.scss',
})
export class BugDetailComponent {
  bug: Bug;
  isUpdating = false;
  errorMessage = '';

  statuses = [
    { value: 'open', label: 'Open' },
    { value: 'in_progress', label: 'In Progress' },
    { value: 'resolved', label: 'Resolved' },
    { value: 'closed', label: 'Closed' },
    { value: 'wont_fix', label: 'Won\'t Fix' },
  ];

  constructor(
    public dialogRef: MatDialogRef<BugDetailComponent>,
    @Inject(MAT_DIALOG_DATA) public data: BugDetailData,
    private bugService: BugService
  ) {
    this.bug = { ...data.bug };
  }

  onStatusChange(newStatus: string): void {
    this.isUpdating = true;
    this.errorMessage = '';

    const payload: UpdateBugRequest = {
      status: newStatus,
    };

    this.bugService.updateBug(this.bug.project_id, this.bug.id, payload).subscribe({
      next: (updated) => {
        this.bug = updated;
        this.isUpdating = false;
      },
      error: (err) => {
        this.isUpdating = false;
        this.errorMessage = err?.error?.detail || 'Failed to update status.';
      },
    });
  }

  onClose(): void {
    this.dialogRef.close(this.bug);
  }
}
