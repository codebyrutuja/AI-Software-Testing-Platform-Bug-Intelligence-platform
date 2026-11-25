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
  TestCase,
  TestCaseService,
  TestSuite,
} from '../../../../core/services/test-case.service';
import { TestCaseDialogComponent } from '../test-case-dialog/test-case-dialog.component';

export interface TestCaseDetailData {
  projectId: string;
  testCase: TestCase;
  suites: TestSuite[];
}

@Component({
  selector: 'app-test-case-detail',
  standalone: true,
  imports: [CommonModule, MatDialogModule, MatButtonModule, MatIconModule],
  templateUrl: './test-case-detail.component.html',
  styleUrl: './test-case-detail.component.scss',
})
export class TestCaseDetailComponent {
  tc: TestCase;
  isDeleting = false;

  constructor(
    private tcService: TestCaseService,
    private dialog: MatDialog,
    public dialogRef: MatDialogRef<TestCaseDetailComponent>,
    @Inject(MAT_DIALOG_DATA) public data: TestCaseDetailData
  ) {
    this.tc = data.testCase;
  }

  onEdit(): void {
    const editRef = this.dialog.open(TestCaseDialogComponent, {
      width: '680px',
      maxHeight: '90vh',
      data: {
        projectId: this.data.projectId,
        testCase: this.tc,
        suites: this.data.suites,
      },
    });

    editRef.afterClosed().subscribe((updated: TestCase | undefined) => {
      if (updated) {
        this.tc = updated;
        this.dialogRef.close({ action: 'updated', testCase: updated });
      }
    });
  }

  onDelete(): void {
    if (!confirm(`Are you sure you want to delete ${this.tc.tc_key}? This will also delete all its steps.`)) {
      return;
    }

    this.isDeleting = true;
    this.tcService.deleteTestCase(this.data.projectId, this.tc.id).subscribe({
      next: () => {
        this.isDeleting = false;
        this.dialogRef.close({ action: 'deleted', testCaseId: this.tc.id });
      },
      error: (err) => {
        this.isDeleting = false;
        alert(err.error?.detail || 'Failed to delete test case.');
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

  getTypeClass(type: string): string {
    switch (type) {
      case 'automated':
        return 'bg-emerald-100 text-emerald-700 border-emerald-200';
      case 'regression':
        return 'bg-blue-100 text-blue-700 border-blue-200';
      case 'smoke':
        return 'bg-orange-100 text-orange-700 border-orange-200';
      case 'sanity':
        return 'bg-cyan-100 text-cyan-700 border-cyan-200';
      default:
        return 'bg-gray-100 text-gray-700 border-gray-200';
    }
  }
}
