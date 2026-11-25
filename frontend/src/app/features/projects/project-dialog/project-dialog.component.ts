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
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import { ProjectService } from '../../../core/services/project.service';

export interface ProjectDialogData {
  orgId: string;
}

@Component({
  selector: 'app-project-dialog',
  standalone: true,
  imports: [
    CommonModule,
    ReactiveFormsModule,
    MatDialogModule,
    MatFormFieldModule,
    MatInputModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './project-dialog.component.html',
  styleUrl: './project-dialog.component.scss',
})
export class ProjectDialogComponent implements OnInit {
  projectForm!: FormGroup;
  isLoading = false;
  errorMessage = '';

  constructor(
    private fb: FormBuilder,
    private projectService: ProjectService,
    public dialogRef: MatDialogRef<ProjectDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: ProjectDialogData
  ) {}

  ngOnInit(): void {
    this.projectForm = this.fb.group({
      name: ['', [Validators.required, Validators.minLength(2), Validators.maxLength(255)]],
      key: [
        '',
        [
          Validators.required,
          Validators.pattern(/^[A-Z]{2,10}$/),
        ],
      ],
      description: ['', [Validators.maxLength(1000)]],
    });
  }

  onKeyInput(event: Event): void {
    const input = event.target as HTMLInputElement;
    const uppercased = input.value.toUpperCase();
    this.projectForm.get('key')?.setValue(uppercased, { emitEvent: false });
  }

  onSubmit(): void {
    if (this.projectForm.invalid || this.isLoading) {
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    const { name, key, description } = this.projectForm.value;

    this.projectService
      .createProject(this.data.orgId, {
        name: name.trim(),
        key: key.trim(),
        description: description ? description.trim() : undefined,
      })
      .subscribe({
        next: (createdProject) => {
          this.isLoading = false;
          this.dialogRef.close(createdProject);
        },
        error: (err) => {
          this.isLoading = false;
          this.errorMessage =
            err.error?.detail ||
            'Failed to create project. Please verify the project key is unique.';
        },
      });
  }

  onCancel(): void {
    this.dialogRef.close();
  }
}
