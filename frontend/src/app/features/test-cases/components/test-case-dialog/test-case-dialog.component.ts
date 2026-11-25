import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  FormArray,
  FormBuilder,
  FormGroup,
  ReactiveFormsModule,
  Validators,
} from '@angular/forms';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import {
  TestCase,
  TestCaseService,
  TestSuite,
} from '../../../../core/services/test-case.service';
import {
  Requirement,
  RequirementService,
} from '../../../../core/services/requirement.service';

export interface TestCaseDialogData {
  projectId: string;
  testCase?: TestCase;
  suites: TestSuite[];
  preselectedSuiteId?: string;
}

@Component({
  selector: 'app-test-case-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatSelectModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './test-case-dialog.component.html',
  styleUrl: './test-case-dialog.component.scss',
})
export class TestCaseDialogComponent implements OnInit {
  tcForm!: FormGroup;
  isLoading = false;
  errorMessage = '';
  isEditMode = false;
  requirements: Requirement[] = [];

  testTypes = [
    { value: 'manual', label: 'Manual' },
    { value: 'automated', label: 'Automated' },
    { value: 'regression', label: 'Regression' },
    { value: 'smoke', label: 'Smoke' },
    { value: 'sanity', label: 'Sanity' },
  ];

  priorities = [
    { value: 'critical', label: 'Critical' },
    { value: 'high', label: 'High' },
    { value: 'medium', label: 'Medium' },
    { value: 'low', label: 'Low' },
  ];

  statuses = [
    { value: 'active', label: 'Active' },
    { value: 'draft', label: 'Draft' },
    { value: 'deprecated', label: 'Deprecated' },
  ];

  constructor(
    private fb: FormBuilder,
    private tcService: TestCaseService,
    private reqService: RequirementService,
    public dialogRef: MatDialogRef<TestCaseDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: TestCaseDialogData
  ) {}

  ngOnInit(): void {
    this.isEditMode = !!this.data.testCase;
    const tc = this.data.testCase;

    this.tcForm = this.fb.group({
      title: [
        tc ? tc.title : '',
        [Validators.required, Validators.minLength(2), Validators.maxLength(255)],
      ],
      suite_id: [tc ? tc.suite_id || '' : this.data.preselectedSuiteId || ''],
      requirement_id: [tc ? tc.requirement_id || '' : ''],
      test_type: [tc ? tc.test_type : 'manual', Validators.required],
      priority: [tc ? tc.priority : 'medium', Validators.required],
      status: [tc ? tc.status : 'active', Validators.required],
      estimated_duration_minutes: [tc ? tc.estimated_duration_minutes : 5, [Validators.min(1)]],
      preconditions: [tc ? tc.preconditions || '' : ''],
      description: [tc ? tc.description || '' : ''],
      steps: this.fb.array([]),
    });

    if (tc && tc.steps && tc.steps.length > 0) {
      tc.steps.forEach((s) => {
        this.addStep(s.action, s.test_data || '', s.expected_result);
      });
    } else {
      // Add one default empty step for convenience
      this.addStep('', '', '');
    }

    // Load project requirements for linking
    this.loadRequirements();
  }

  get steps(): FormArray {
    return this.tcForm.get('steps') as FormArray;
  }

  addStep(action = '', testData = '', expectedResult = ''): void {
    const stepGroup = this.fb.group({
      action: [action, Validators.required],
      test_data: [testData],
      expected_result: [expectedResult, Validators.required],
    });
    this.steps.push(stepGroup);
  }

  removeStep(index: number): void {
    this.steps.removeAt(index);
    if (this.steps.length === 0) {
      this.addStep();
    }
  }

  loadRequirements(): void {
    this.reqService.listRequirements(this.data.projectId).subscribe({
      next: (res) => {
        this.requirements = res.items;
      },
    });
  }

  onSubmit(): void {
    if (this.tcForm.invalid || this.isLoading) {
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    const formVal = this.tcForm.value;
    const stepsPayload = this.steps.value.map((s: any, idx: number) => ({
      step_number: idx + 1,
      action: s.action.trim(),
      test_data: s.test_data ? s.test_data.trim() : undefined,
      expected_result: s.expected_result.trim(),
    }));

    if (this.isEditMode && this.data.testCase) {
      this.tcService
        .updateTestCase(this.data.projectId, this.data.testCase.id, {
          title: formVal.title.trim(),
          suite_id: formVal.suite_id || undefined,
          requirement_id: formVal.requirement_id || undefined,
          test_type: formVal.test_type,
          priority: formVal.priority,
          status: formVal.status,
          estimated_duration_minutes: formVal.estimated_duration_minutes,
          preconditions: formVal.preconditions ? formVal.preconditions.trim() : undefined,
          description: formVal.description ? formVal.description.trim() : undefined,
          steps: stepsPayload,
        })
        .subscribe({
          next: (res) => {
            this.isLoading = false;
            this.dialogRef.close(res);
          },
          error: (err) => {
            this.isLoading = false;
            this.errorMessage = err.error?.detail || 'Failed to update test case.';
          },
        });
    } else {
      this.tcService
        .createTestCase(this.data.projectId, {
          title: formVal.title.trim(),
          suite_id: formVal.suite_id || undefined,
          requirement_id: formVal.requirement_id || undefined,
          test_type: formVal.test_type,
          priority: formVal.priority,
          status: formVal.status,
          estimated_duration_minutes: formVal.estimated_duration_minutes,
          preconditions: formVal.preconditions ? formVal.preconditions.trim() : undefined,
          description: formVal.description ? formVal.description.trim() : undefined,
          steps: stepsPayload,
        })
        .subscribe({
          next: (res) => {
            this.isLoading = false;
            this.dialogRef.close(res);
          },
          error: (err) => {
            this.isLoading = false;
            this.errorMessage = err.error?.detail || 'Failed to create test case.';
          },
        });
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
