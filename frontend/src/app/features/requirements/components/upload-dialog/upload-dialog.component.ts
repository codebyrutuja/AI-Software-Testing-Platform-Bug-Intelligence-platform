import { Component, Inject } from '@angular/core';
import { CommonModule } from '@angular/common';
import {
  MAT_DIALOG_DATA,
  MatDialogModule,
  MatDialogRef,
} from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatProgressSpinnerModule } from '@angular/material/progress-spinner';
import {
  DocumentUploadResponse,
  RequirementService,
} from '../../../../core/services/requirement.service';

export interface UploadDialogData {
  projectId: string;
}

@Component({
  selector: 'app-upload-dialog',
  standalone: true,
  imports: [
    CommonModule,
    MatDialogModule,
    MatButtonModule,
    MatIconModule,
    MatProgressSpinnerModule,
  ],
  templateUrl: './upload-dialog.component.html',
  styleUrl: './upload-dialog.component.scss',
})
export class UploadDialogComponent {
  selectedFile: File | null = null;
  isDragging = false;
  isLoading = false;
  errorMessage = '';

  constructor(
    private reqService: RequirementService,
    public dialogRef: MatDialogRef<UploadDialogComponent>,
    @Inject(MAT_DIALOG_DATA) public data: UploadDialogData
  ) {}

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = true;
  }

  onDragLeave(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = false;
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    this.isDragging = false;

    if (event.dataTransfer && event.dataTransfer.files.length > 0) {
      this.handleFile(event.dataTransfer.files[0]);
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    if (input.files && input.files.length > 0) {
      this.handleFile(input.files[0]);
    }
  }

  handleFile(file: File): void {
    const lowerName = file.name.toLowerCase();
    const validExtensions = ['.md', '.txt', '.pdf'];
    const isValid = validExtensions.some((ext) => lowerName.endsWith(ext));

    if (!isValid) {
      this.errorMessage = 'Invalid file format. Please upload a .md, .txt, or .pdf file.';
      this.selectedFile = null;
      return;
    }

    if (file.size > 10 * 1024 * 1024) {
      this.errorMessage = 'File size exceeds maximum limit of 10 MB.';
      this.selectedFile = null;
      return;
    }

    this.errorMessage = '';
    this.selectedFile = file;
  }

  onUpload(): void {
    if (!this.selectedFile || this.isLoading) {
      return;
    }

    this.isLoading = true;
    this.errorMessage = '';

    this.reqService
      .uploadDocument(this.data.projectId, this.selectedFile)
      .subscribe({
        next: (res: DocumentUploadResponse) => {
          this.isLoading = false;
          this.dialogRef.close(res);
        },
        error: (err) => {
          this.isLoading = false;
          this.errorMessage =
            err.error?.detail || 'Failed to upload and parse document.';
        },
      });
  }

  onCancel(): void {
    this.dialogRef.close();
  }

  formatFileSize(bytes: number): string {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
  }
}
