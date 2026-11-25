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
  Requirement,
  RequirementService,
} from '../../../../core/services/requirement.service';

export interface RequirementDialogData {
  projectId: string;
  requirement?: Requirement;
}

@Component({
  selector: 'app-requirement-dialog',
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
  templateUrl: './requirement-dialog.component.html',
  styleUrl: './requirement-dialog.component.scss',
})
export class RequirementDialogComponent implements OnInit {
  reqForm!: FormGroup;
  isLoading = false;
  errorMessage = '';
  isEditMode = false;

  categories = [
    { value: 'functional', label: 'Functional' },
    { value: 'non_functional', label: 'Non-Functional' },
    { value: 'security', label: 'Security' },
    { value: 'ui_ux', label: 'UI / UX' },
    { value: 'performance', label: 'Performance' },
  ];

  priorities = [
    { value: 'critical', label: 'Critical' },
    { value: 'high', label: 'High' },
    { value: 'medium', label: 'Medium' },
    { value: 'low', label: 'Low' },
  ];

  statuses = [
    { value: 'draft', label: 'Draft' },
    { value: 'approved', label: 'Approved' },
    { value: 'deprecated', label: 'Deprecated' },
  ];

  constructor(
    private fb: FormBuilder,
    private reqService: RequirementService,
    public dialogRef: MatDialogRef<RequirementDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: RequirementDialogData
  ) {}

  ngOnInit(): void {
    this.isEditMode = !!this.data.requirement;
    const req = this.data.requirement;

    this.reqForm = this.fb.group({
      title: [
        req ? req.title : '',
        [Validators.required, Validators.minLength(2), Validators.maxLength(255)],
      ],
      description: [req ? req.description || '' : ''],
      category: [req ? req.category : 'functional', [Validators.required]],
      priority: [req ? req.priority : 'medium', [Validators.required]],
      status: [req ? req.status : 'draft', [Validators.required]],
      criteriaList: this.fb.array([]),
      newCriterion: [''],
    });

    if (req && req.acceptance_criteria && req.acceptance_criteria.length > 0) {
      req.acceptance_criteria.forEach((ac) => {
        this.addCriterionControl(ac.criteria);
      });
    }
  }

  get criteriaList(): FormArray {
    return this.reqForm.get('criteriaList') as FormArray;
  }

  addCriterionControl(text: string): void {
    if (text.trim()) {
      this.criteriaList.push(this.fb.control(text.trim(), Validators.required));
    }
  }

  addCriterionFromInput(): void {
    const control = this.reqForm.get('newCriterion');
    if (control && control.value && control.value.trim()) {
      this.addCriterionControl(control.value.trim());
      control.setValue('');
    }
  }

  removeCriterion(index: number): void {
    this.criteriaList.removeAt(index);
  }

  onSubmit(): void {
    if (this.reqForm.invalid || this.isLoading) {
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    const formVal = this.reqForm.value;
    const criteriaStrings: string[] = this.criteriaList.value;

    if (this.isEditMode && this.data.requirement) {
      this.reqService
        .updateRequirement(this.data.projectId, this.data.requirement.id, {
          title: formVal.title.trim(),
          description: formVal.description ? formVal.description.trim() : undefined,
          category: formVal.category,
          priority: formVal.priority,
          status: formVal.status,
          acceptance_criteria: criteriaStrings,
        })
        .subscribe({
          next: (res) => {
            this.isLoading = false;
            this.dialogRef.close(res);
          },
          error: (err) => {
            this.isLoading = false;
            this.errorMessage = err.error?.detail || 'Failed to update requirement.';
          },
        });
    } else {
      this.reqService
        .createRequirement(this.data.projectId, {
          title: formVal.title.trim(),
          description: formVal.description ? formVal.description.trim() : undefined,
          category: formVal.category,
          priority: formVal.priority,
          status: formVal.status,
          acceptance_criteria: criteriaStrings,
        })
        .subscribe({
          next: (res) => {
            this.isLoading = false;
            this.dialogRef.close(res);
          },
          error: (err) => {
            this.isLoading = false;
            this.errorMessage = err.error?.detail || 'Failed to create requirement.';
          },
        });
    }
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
