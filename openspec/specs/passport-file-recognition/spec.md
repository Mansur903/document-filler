# Passport File Recognition Specification

## Purpose

Enables users to select a local passport scan in JPG, JPEG, or PDF format and extract the supported passport fields through the desktop application.

## Requirements

### Requirement: Supported passport file selection

The system SHALL let the user select exactly one local `.jpg`, `.jpeg`, or `.pdf` file through the operating system file picker.

#### Scenario: Select a JPEG passport image

- **WHEN** the user selects a `.jpg` or `.jpeg` file
- **THEN** the system stores it as the current passport input and displays its file name and image preview

#### Scenario: Select a PDF passport document

- **WHEN** the user selects a `.pdf` file
- **THEN** the system stores it as the current passport input and displays its file name and PDF file type

#### Scenario: Cancel passport file selection

- **WHEN** the user cancels the native file picker
- **THEN** the system leaves the current passport input unchanged

#### Scenario: Replace the selected passport file

- **WHEN** the user chooses another supported passport file
- **THEN** the system replaces the current input and clears recognition results associated with the previous file

### Requirement: Minimal renderer access

The system MUST keep the selected local file path and file-system access outside the Angular renderer and SHALL expose only the file name, file type, and any preview data required for the UI.

#### Scenario: PDF metadata is returned to Angular

- **WHEN** a PDF is selected
- **THEN** Angular receives no local file path and no unrestricted Node.js or Electron capability

#### Scenario: JPEG preview is returned to Angular

- **WHEN** a JPG or JPEG image is selected
- **THEN** Angular receives safe preview data without receiving the local file path

### Requirement: Passport recognition from supported files

The system SHALL run the existing local passport OCR flow for a selected JPG, JPEG, or PDF file and return the existing structured passport-data fields to Angular.

#### Scenario: Recognize a JPEG passport image

- **WHEN** the user starts recognition for a selected JPG or JPEG passport image
- **THEN** the system extracts passport data with the same behavior available before PDF support

#### Scenario: Recognize a single-page passport PDF

- **WHEN** the user starts recognition for a valid single-page PDF containing a passport scan
- **THEN** the system extracts supported passport fields from the rendered PDF page

#### Scenario: Recognize a passport PDF with photo and signature pages

- **WHEN** the user starts recognition for a valid PDF containing a passport photo page and a signature page
- **THEN** the system identifies the photo page by its Russian passport MRZ, extracts supported passport fields only from that page, and ignores the signature page

#### Scenario: PDF cannot be processed

- **WHEN** the selected PDF is invalid, unreadable, encrypted without access, or contains no renderable page
- **THEN** recognition fails without exposing local file-system details to Angular and the UI presents a recognition error

### Requirement: Local PDF processing

The system MUST process the selected PDF locally using resources bundled with or installed for the desktop application and MUST NOT upload the passport file to an HTTP service.

#### Scenario: Offline PDF recognition

- **WHEN** the application and OCR resources are installed and the device has no network connection
- **THEN** the system can select and recognize a supported PDF without requiring a remote API
