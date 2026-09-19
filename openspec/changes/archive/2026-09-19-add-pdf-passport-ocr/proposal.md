# Proposal

## Why

Passport scans are often distributed as PDF documents, but the application currently accepts only JPG and JPEG images. Users need to select a passport PDF from the Angular UI and run the existing local PaddleOCR recognition flow without converting the document manually.

## What Changes

- Extend the native passport-file picker to accept `.pdf` in addition to `.jpg` and `.jpeg`.
- Represent the selected input as a passport document rather than an image-only value while exposing only the minimum metadata needed by Angular.
- Update the Angular UI to show the selected PDF and allow recognition or replacement using the same workflow as images.
- Allow the local OCR worker to validate and process a PDF containing a passport photo page and a signature page.
- Identify the passport photo page by its Russian passport MRZ, ignore the signature page, and return the existing `PassportData` shape.
- Keep JPG/JPEG selection, preview, and recognition behavior compatible with the current application.

## Capabilities

### New Capabilities

- `passport-file-recognition`: Selection and local OCR recognition of passport data from supported image and PDF files.

### Modified Capabilities

None.

## Impact

- Angular passport-file selection state, labels, error messages, and rendering.
- Shared Electron/Angular API and UI models.
- Electron file-picker IPC handler and stored selected-file path.
- Python OCR input validation and multi-page result handling.
- OCR packaging metadata/dependencies if PDF runtime files are not already collected by the standalone build.
- Existing Angular and OCR checks for JPG/JPEG compatibility plus new PDF coverage.
