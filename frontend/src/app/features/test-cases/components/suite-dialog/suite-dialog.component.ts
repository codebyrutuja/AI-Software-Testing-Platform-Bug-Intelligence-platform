import { Component, Inject, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormBuilder, FormGroup, ReactiveFormsModule, Validators } from '@angular/forms';
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
  TestSuite,
  TestCaseService,
} from '../../../../core/services/test-case.service';

export interface SuiteDialogData {
  projectId: string;
  suite?: TestSuite;
  existingSuites: TestSuite[];
}

@Component({
  selector: 'app-suite-dialog',
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
  templateUrl: './suite-dialog.component.html',
  styleUrl: './suite-dialog.component.scss',
})
export class SuiteDialogComponent implements OnInit {
  suiteForm!: FormGroup;
  isLoading = false;
  errorMessage = '';
  isEditMode = false;

  constructor(
    private fb: FormBuilder,
    private tcService: TestCaseService,
    public dialogRef: MatDialogRef<SuiteDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: SuiteDialogData
  ) {}

  ngOnInit(): void {
    this.isEditMode = !!this.data.suite;
    const suite = this.data.suite;

    this.suiteForm = this.fb.group({
      name: [
        suite ? suite.name : '',
        [Validators.required, Validators.minLength(2), Validators.maxLength(255)],
      ],
      description: [suite ? suite.description || '' : ''],
      parent_suite_id: [suite ? suite.parent_suite_id || '' : ''],
    });
  }

  onSubmit(): void {
    if (this.suiteForm.invalid || this.isLoading) {
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    const { name, description, parent_suite_id } = this.suiteForm.value;

    if (this.isEditMode && this.data.suite) {
      this.tcService
        .updateSuite(this.data.projectId, this.data.suite.id, {
          name: name.trim(),
          description: description ? description.trim() : undefined,
          parent_suite_id: parent_suite_id || undefined,
        })
        .subscribe({
          next: (res) => {
            this.isLoading = false;
            this.dialogRef.close(res);
          },
          error: (err) => {
            this.isLoading = false;
            this.errorMessage = err.error?.detail || 'Failed to update test suite.';
          },
        });
    } else {
      this.tcService
        .createSuite(this.data.projectId, {
          name: name.trim(),
          description: description ? description.trim() : undefined,
          parent_suite_id: parent_suite_id || undefined,
        })
        .subscribe({
          next: (res) => {
            this.isLoading = false;
            this.dialogRef.close(res);
          },
          error: (err) => {
            this.isLoading = false;
            this.errorMessage = err.error?.detail || 'Failed to create test suite.';
          },
        });
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
