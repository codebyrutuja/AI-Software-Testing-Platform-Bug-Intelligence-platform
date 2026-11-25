import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router, RouterLink } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { MatTooltipModule } from '@angular/material/tooltip';
import { MatDialog, MatDialogModule } from '@angular/material/dialog';

import {
  SubmitItemResultRequest,
  TestRun,
  TestRunItem,
  TestRunService,
} from '../../../../core/services/test-run.service';
import { TestCase, TestCaseService } from '../../../../core/services/test-case.service';
import { BugDialogComponent } from '../../../bug-tracker/components/bug-dialog/bug-dialog.component';

@Component({
  selector: 'app-run-execution',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    RouterLink,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
    MatTooltipModule,
    MatDialogModule,
  ],
  templateUrl: './run-execution.component.html',
  styleUrl: './run-execution.component.scss',
})
export class RunExecutionComponent implements OnInit {
  projectId = '';
  runId = '';
  run: TestRun | null = null;
  activeItem: TestRunItem | null = null;
  activeTestCase: TestCase | null = null;

  isLoading = true;
  isLoadingCase = false;
  isSubmitting = false;
  errorMessage = '';

  // Form for active execution
  selectedResult: 'passed' | 'failed' | 'blocked' | 'skipped' = 'passed';
  failureNotes = '';
  actualDuration: number | null = null;

  constructor(
    private route: ActivatedRoute,
    private router: Router,
    private runService: TestRunService,
    private tcService: TestCaseService,
    private dialog: MatDialog
  ) {}

  ngOnInit(): void {
    this.route.paramMap.subscribe((params) => {
      this.projectId = params.get('projectId') || '';
      this.runId = params.get('runId') || '';
      if (this.projectId && this.runId) {
        this.loadRun();
      }
    });
  }

  loadRun(): void {
    this.isLoading = true;
    this.runService.getRun(this.projectId, this.runId).subscribe({
      next: (run) => {
        this.run = run;
        this.isLoading = false;

        // Auto-select first not_run item, or first item
        if (run.items.length > 0) {
          const notRunItem = run.items.find((i) => i.result === 'not_run');
          this.selectItem(notRunItem || run.items[0]);
        }
      },
      error: () => {
        this.isLoading = false;
        this.errorMessage = 'Failed to load test run details.';
      },
    });
  }

  selectItem(item: TestRunItem): void {
    this.activeItem = item;
    this.selectedResult = item.result !== 'not_run' ? item.result : 'passed';
    this.failureNotes = item.failure_notes || '';
    this.actualDuration = item.actual_duration_minutes || null;

    if (item.test_case_id) {
      this.isLoadingCase = true;
      this.tcService.getTestCase(this.projectId, item.test_case_id).subscribe({
        next: (tc) => {
          this.activeTestCase = tc;
          this.isLoadingCase = false;
        },
        error: () => {
          this.isLoadingCase = false;
          this.activeTestCase = null;
        },
      });
    } else {
      this.activeTestCase = null;
    }
  }

  submitResult(result: 'passed' | 'failed' | 'blocked' | 'skipped'): void {
    if (!this.activeItem || !this.run) return;

    if (result === 'failed' && !this.failureNotes.trim()) {
      this.errorMessage = 'Please provide failure notes describing what went wrong.';
      return;
    }

    this.isSubmitting = true;
    this.errorMessage = '';

    const payload: SubmitItemResultRequest = {
      result,
      failure_notes: result === 'failed' ? this.failureNotes.trim() : undefined,
      actual_duration_minutes: this.actualDuration || undefined,
    };

    this.runService
      .submitItemResult(this.projectId, this.run.id, this.activeItem.id, payload)
      .subscribe({
        next: (updatedItem) => {
          this.isSubmitting = false;

          // Update local state
          const idx = this.run!.items.findIndex((i) => i.id === updatedItem.id);
          if (idx !== -1) {
            this.run!.items[idx] = updatedItem;
          }
          this.activeItem = updatedItem;

          // Reload run to get updated progress stats
          this.reloadProgress();

          // Move to next unexecuted item if available
          const nextItem = this.run!.items.find((i) => i.result === 'not_run');
          if (nextItem) {
            this.selectItem(nextItem);
          }
        },
        error: (err) => {
          this.isSubmitting = false;
          this.errorMessage = err?.error?.detail || 'Failed to submit result.';
        },
      });
  }

  reloadProgress(): void {
    this.runService.getRun(this.projectId, this.runId).subscribe({
      next: (r) => {
        this.run = r;
      },
    });
  }

  openBugReport(): void {
    if (!this.activeItem) return;
    const dialogRef = this.dialog.open(BugDialogComponent, {
      width: '650px',
      data: {
        projectId: this.projectId,
        testCaseId: this.activeItem.test_case_id,
        testCaseKey: this.activeItem.tc_key,
        testCaseTitle: this.activeItem.tc_title,
        testRunItemId: this.activeItem.id,
        failureNotes: this.activeItem.failure_notes || this.failureNotes,
      },
    });

    dialogRef.afterClosed().subscribe((createdBug) => {
      if (createdBug) {
        // Bug reported successfully
      }
    });
  }

  getProgressPercentage(): number {
    if (!this.run || this.run.total_count === 0) return 0;
    const executed = this.run.total_count - this.run.not_run_count;
    return Math.round((executed / this.run.total_count) * 100);
  }
}
