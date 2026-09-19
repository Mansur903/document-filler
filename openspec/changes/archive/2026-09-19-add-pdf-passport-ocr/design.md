# Design

## Context

See `proposal.md` for motivation and `specs/passport-file-recognition/spec.md` for observable behavior.

The current Angular UI calls a narrow preload API to select an image. Electron main retains the local path, returns a JPEG data URL for preview, and later passes the retained path to a Python OCR worker. The worker validates JPG/JPEG input, invokes PaddleOCR, combines recognized text blocks, and passes them to the Russian passport parser. The packaged application runs the same worker as a PyInstaller-built `ocr.exe` with local OCR models.

The installed PaddleOCR/PaddleX pipeline already accepts PDF paths and uses `pypdfium2` to render their pages. This allows PDF support without adding an HTTP service or a separate PDF conversion pipeline. Multi-page results must remain separated because page-relative OCR coordinates cannot be safely combined before parsing.

## Goals / Non-Goals

**Goals:**

- Preserve the Angular → preload → Electron main → OCR worker trust boundary.
- Use one user workflow for selecting and recognizing JPG, JPEG, and PDF passport inputs.
- Keep image preview behavior while representing a PDF without sending its contents or path to Angular.
- Parse PDF pages independently, identify the passport photo page by its Russian passport MRZ, and ignore the signature page.
- Keep development and packaged Windows behavior aligned.

**Non-Goals:**

- Rendering an interactive PDF viewer in Angular.
- Extracting embedded PDF text instead of running OCR on rendered pages.
- Supporting formats other than JPG, JPEG, and PDF.
- Changing the passport fields, Russian-passport parser rules, DOCX generation, or OCR models.
- Adding remote storage or network OCR.

## Decisions

### Generalize the selected input model and IPC naming

Replace the image-specific selection contract with a passport-file contract shared by Electron and Angular. The result will contain `name`, a discriminated `type` (`image` or `pdf`), and `previewDataUrl`, which is populated only for images. Rename the preload method and IPC channel to describe passport-file selection rather than image-only selection. Electron main remains the sole owner of the absolute path used by recognition.

This makes PDF state explicit and prevents Angular from inferring file type from display text. Keeping the old `SelectedImage` model and adding nullable PDF fields was rejected because it would preserve misleading image-only terminology throughout the application.

### Keep PDF contents out of the renderer

For JPG/JPEG, Electron continues to return a data URL required by the existing `<img>` preview. For PDF, Electron returns only the file name, type, and a null preview. Angular renders a compact PDF file state instead of an embedded PDF document.

Returning a base64 PDF or a local `file://` URL was rejected because neither is required for recognition, both increase renderer exposure, and a base64 PDF can consume substantial renderer memory.

### Use PaddleOCR/PaddleX native PDF rendering

The OCR worker will accept `.pdf` in its validated extension set and pass the path directly to the existing OCR pipeline. PaddleX already renders PDF pages through `pypdfium2`, so a separate converter such as Poppler is unnecessary. The standalone OCR build must be verified to include the PDFium runtime and metadata that this path requires.

Adding a Node-side or separate Python PDF-to-image conversion stage was rejected because it duplicates behavior already present in the pinned OCR stack and would add temporary-file handling and packaging complexity.

### Select the passport photo page by MRZ

Each result emitted for a PDF page will be converted into its own text-block list and parsed independently in document order. A page is treated as the passport photo page only when the parser finds the Russian passport MRZ, including the `P<RUS` prefix and its associated second MRZ line. The worker returns the parsed data from the first page with that MRZ and stops processing later pages. A signature page has no passport MRZ, so its OCR text is discarded instead of being combined with or compared to the photo page.

A PDF that yields no page results is treated as an OCR failure. A renderable PDF whose pages contain no recognizable Russian passport MRZ returns the same empty field structure as an unrecognized image.

Combining all page blocks was rejected because coordinates restart on every page and text from the signature page could be paired with MRZ or visual labels from the photo page. Ranking pages by populated fields was rejected because unrelated text on the signature page could produce coincidental values. Detecting the photograph itself with a separate computer-vision model was rejected because the MRZ already provides a document-specific marker for the required page.

### Preserve the current recognition response

The recognition IPC response remains `PassportData`; no page number or PDF-specific details are exposed to Angular. This keeps passport form population and DOCX generation unchanged. Selection state is reset when a new file is accepted, while canceling selection keeps the existing file and recognition state.

## Risks / Trade-offs

- **[Large or many-page PDFs increase recognition time]** → Process pages sequentially, keep the existing worker timeout, stop as soon as a Russian passport MRZ is found, and retain the UI busy state for the complete operation.
- **[PDFium resources may be omitted from `ocr.exe`]** → Verify a packaged OCR executable with a PDF fixture and adjust PyInstaller collection only if the pinned dependencies are not discovered automatically.
- **[OCR may fail to read the MRZ on the photo page]** → Keep pages isolated and return no recognized passport data when no page has a recognizable Russian passport MRZ instead of falling back to the signature page.
- **[Renaming the preload API and channel can temporarily desynchronize layers]** → Update Electron and Angular model copies, preload, main, component, and tests in one change, then run both Angular and Electron type-checks.
- **[Image data URLs still duplicate the image in renderer memory]** → Retain the existing behavior for compatibility; PDF support does not introduce an additional large renderer payload.

## Migration Plan

1. Introduce the generalized passport-file model and update the IPC/preload contract across Electron and Angular.
2. Extend the native picker and Angular selected-file presentation while retaining JPG/JPEG preview behavior.
3. Extend and verify the OCR worker's PDF validation, per-page parsing, MRZ-based photo-page selection, and signature-page exclusion.
4. Run unit/type/build checks, then validate both development Electron and the packaged Windows OCR executable with JPG and PDF inputs.

Rollback consists of reverting the change; no stored user data or document format migration is required.
