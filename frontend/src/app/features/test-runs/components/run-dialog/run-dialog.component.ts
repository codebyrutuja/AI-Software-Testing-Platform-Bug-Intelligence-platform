import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { TestCase, TestCaseService } from '../../../../core/services/test-case.service';
import { CreateTestRunRequest } from '../../../../core/services/test-run.service';

export interface RunDialogData {
  projectId: string;
}

@Component({
  selector: 'app-run-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './run-dialog.component.html',
  styleUrl: './run-dialog.component.scss',
})
export class RunDialogComponent implements OnInit {
  name = '';
  description = '';
  environment = 'staging';

  testCases: TestCase[] = [];
  selectedCaseIds: Set<string> = new Set();
  isLoadingCases = false;
  errorMessage = '';

  environments = [
    { value: 'staging', label: 'Staging' },
    { value: 'qa', label: 'QA' },
    { value: 'local', label: 'Local' },
    { value: 'production', label: 'Production' },
  ];

  constructor(
    public dialogRef: MatDialogRef<RunDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: RunDialogData,
    private tcService: TestCaseService
  ) {}

  ngOnInit(): void {
    this.loadTestCases();
  }

  loadTestCases(): void {
    this.isLoadingCases = true;
    this.tcService.getTestCases(this.data.projectId, { limit: 100 }).subscribe({
      next: (res) => {
        this.testCases = res.items;
        // Default select all active test cases
        this.testCases.forEach((tc) => {
          if (tc.status === 'active') {
            this.selectedCaseIds.add(tc.id);
          }
        });
        this.isLoadingCases = false;
      },
      error: () => {
        this.isLoadingCases = false;
        this.errorMessage = 'Failed to load test cases.';
      },
    });
  }

  toggleCase(id: string): void {
    if (this.selectedCaseIds.has(id)) {
      this.selectedCaseIds.delete(id);
    } else {
      this.selectedCaseIds.add(id);
    }
  }

  toggleAll(): void {
    if (this.selectedCaseIds.size === this.testCases.length) {
      this.selectedCaseIds.clear();
    } else {
      this.testCases.forEach((tc) => this.selectedCaseIds.add(tc.id));
    }
  }

  onSave(): void {
    if (!this.name.trim()) {
      this.errorMessage = 'Please provide a test run name.';
      return;
    }
    if (this.selectedCaseIds.size === 0) {
      this.errorMessage = 'Please select at least one test case.';
      return;
    }

    const payload: CreateTestRunRequest = {
      name: this.name.trim(),
      description: this.description.trim() || undefined,
      environment: this.environment,
      test_case_ids: Array.from(this.selectedCaseIds),
    };

    this.dialogRef.close(payload);
  }
}
