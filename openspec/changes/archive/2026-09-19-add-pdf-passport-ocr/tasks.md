# Tasks

## 1. Passport File Contract

- [x] 1.1 Replace the image-only selection models in Electron and Angular with a typed passport-file result containing name, `image`/`pdf` type, and nullable image preview data; verify both model copies expose the same contract without a local path
- [x] 1.2 Rename the image-selection IPC constant and preload method to passport-file terminology, update all call sites, and verify `npm run build:electron` passes
- [x] 1.3 Extend the Electron native picker to accept one JPG, JPEG, or PDF, retain the path only in main, and return type-appropriate metadata; verify cancel preserves the previous selection and unsupported extensions are rejected

## 2. Angular Selection Experience

- [x] 2.1 Update Angular state and handlers to select, replace, and recognize a passport file while clearing results only after a new file is accepted; verify the component type-checks without `any`
- [x] 2.2 Update the selection panel text and rendering so images keep their preview and PDFs show a concise PDF file state with the selected name; verify recognition and replacement controls are available for both types
- [x] 2.3 Update Angular component tests for JPEG selection, PDF selection, cancel, and replacement behavior; verify `npm test -- --watch=false` passes

## 3. PDF OCR

- [x] 3.1 Extend OCR input validation to accept `.pdf` while keeping file existence and supported-extension checks; verify unsupported input still fails with a controlled error
- [x] 3.2 Parse PaddleOCR results page by page, return data only from the first page with a recognizable Russian passport MRZ, and ignore pages without that MRZ; verify focused Python tests cover single-page input, photo-then-signature order, signature-then-photo order, unreadable MRZ, empty pages, and no page results
- [x] 3.3 Verify the pinned PaddleOCR/PaddleX environment recognizes the photo page and ignores the signature page in an actual passport PDF during development, and adjust Python requirements only if the existing PDF runtime is missing

## 4. Build and Integration Verification

- [x] 4.1 Run the Angular production build and Electron TypeScript build, fixing contract or template errors until `npm run build` passes
- [ ] 4.2 Run Electron in development mode and manually verify JPG/JPEG and PDF selection, display, replacement, recognition, and DOCX form population
- [x] 4.3 Build the standalone OCR worker and verify `ocr.exe` recognizes JPG/JPEG and PDF inputs without Python installed or network access
- [ ] 4.4 Build the Windows installer and verify the installed application can select and recognize a PDF; confirm the packaged PDFium resources load successfully
