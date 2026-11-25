import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { MatDialogRef, MAT_DIALOG_DATA, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { BugService, CreateBugRequest } from '../../../../core/services/bug.service';
import { TestCase, TestCaseService } from '../../../../core/services/test-case.service';
import { Requirement, RequirementService } from '../../../../core/services/requirement.service';

export interface BugDialogData {
  projectId: string;
  testCaseId?: string;
  testCaseKey?: string;
  testCaseTitle?: string;
  testRunItemId?: string;
  failureNotes?: string;
}

@Component({
  selector: 'app-bug-dialog',
  standalone: true,
  imports: [
    CommonModule,
    FormsModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './bug-dialog.component.html',
  styleUrl: './bug-dialog.component.scss',
})
export class BugDialogComponent implements OnInit {
  title = '';
  description = '';
  stepsToReproduce = '';
  expectedBehavior = '';
  actualBehavior = '';
  severity = 'medium';
  priority = 'medium';
  environment = 'staging';
  browserOs = '';
  testCaseId: string | undefined;
  requirementId: string | undefined;

  testCases: TestCase[] = [];
  requirements: Requirement[] = [];
  isLoading = false;
  isSaving = false;
  errorMessage = '';

  severities = [
    { value: 'critical', label: 'Critical' },
    { value: 'high', label: 'High' },
    { value: 'medium', label: 'Medium' },
    { value: 'low', label: 'Low' },
  ];

  priorities = [
    { value: 'critical', label: 'Critical' },
    { value: 'high', label: 'High' },
    { value: 'medium', label: 'Medium' },
    { value: 'low', label: 'Low' },
  ];

  constructor(
    public dialogRef: MatDialogRef<BugDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: BugDialogData,
    private bugService: BugService,
    private tcService: TestCaseService,
    private reqService: RequirementService
  ) {}

  ngOnInit(): void {
    if (this.data.testCaseId) {
      this.testCaseId = this.data.testCaseId;
      if (this.data.testCaseTitle) {
        this.title = `Bug found in ${this.data.testCaseKey || 'TC'}: ${this.data.testCaseTitle}`;
      }
    }
    if (this.data.failureNotes) {
      this.actualBehavior = this.data.failureNotes;
    }

    this.loadRelations();
  }

  loadRelations(): void {
    this.isLoading = true;
    this.tcService.getTestCases(this.data.projectId, { limit: 100 }).subscribe({
      next: (res) => {
        this.testCases = res.items;
      },
    });

    this.reqService.listRequirements(this.data.projectId, { limit: 100 }).subscribe({
      next: (res) => {
        this.requirements = res.items;
        this.isLoading = false;
      },
      error: () => {
        this.isLoading = false;
      },
    });
  }

  onSave(): void {
    if (!this.title.trim()) {
      this.errorMessage = 'Please provide a bug summary title.';
      return;
    }

    this.isSaving = true;
    this.errorMessage = '';

    const payload: CreateBugRequest = {
      title: this.title.trim(),
      description: this.description.trim() || undefined,
      steps_to_reproduce: this.stepsToReproduce.trim() || undefined,
      expected_behavior: this.expectedBehavior.trim() || undefined,
      actual_behavior: this.actualBehavior.trim() || undefined,
      severity: this.severity,
      priority: this.priority,
      environment: this.environment.trim() || undefined,
      browser_os: this.browserOs.trim() || undefined,
      test_case_id: this.testCaseId || undefined,
      requirement_id: this.requirementId || undefined,
      test_run_item_id: this.data.testRunItemId || undefined,
    };

    const request$ = this.data.testRunItemId
      ? this.bugService.quickReportFromRunItem(
          this.data.projectId,
          '',
          this.data.testRunItemId,
          payload
        )
      : this.bugService.createBug(this.data.projectId, payload);

    request$.subscribe({
      next: (created) => {
        this.isSaving = false;
        this.dialogRef.close(created);
      },
      error: (err) => {
        this.isSaving = false;
        this.errorMessage =
          err?.error?.detail || 'Failed to report bug. Please check required fields.';
      },
    });
  }
}
