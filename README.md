# DocumentFiller

This project was generated using [Angular CLI](https://github.com/angular/angular-cli) version 22.1.7.

## Development server

To start a local development server, run:

```bash
ng serve
```

Once the server is running, open your browser and navigate to `http://localhost:4200/`. The application will automatically reload whenever you modify any of the source files.

## Code scaffolding

Angular CLI includes powerful code scaffolding tools. To generate a new component, run:

```bash
ng generate component component-name
```

For a complete list of available schematics (such as `components`, `directives`, or `pipes`), run:

```bash
ng generate --help
```

## Building

To build the project run:

```bash
ng build
```

This will compile your project and store the build artifacts in the `dist/` directory. By default, the production build optimizes your application for performance and speed.

## Local document OCR

Russian international passport and UAE Residence Permit OCR run locally with Python 3.11, PaddlePaddle, and PaddleOCR. Select the matching document type in the application before recognizing a JPG, JPEG, PNG, or PDF file.

Create the isolated environment and install the pinned development dependencies:

```powershell
python -m venv .venv-ocr
.\.venv-ocr\Scripts\python.exe -m pip install -r ocr\requirements-build.txt
```

The OCR models are downloaded to the local PaddleX cache on first recognition. Recognized values are merged into the shared form without replacing non-empty OCR or manually entered values, so the two document types can be processed in either order. Use **New user** to clear the form and current input while keeping the selected DOCX template.

## Windows installer

Build the application, the standalone OCR runtime, and the NSIS installer:

```powershell
npm run package:win
```

The installer is created in `release`. It contains the Python runtime, PaddleOCR, and both OCR models, so the destination computer does not need Python, Node.js, or an internet connection.

## DOCX templates

Select a `.docx` template after entering or recognizing personal data. The template can contain these placeholders:

```text
{surname}
{givenName}
{dateOfBirth}
{placeOfBirth}
{currentNationality}
{sex}
{numberOfTravelDocument}
{dateOfIssue}
{validUntil}
{issuedByCountry}
{residencepermitID}
{visaID}
{visaValidUntil}
{currentOccupation}
{employer}
{email}
{address}
{phone}
```

The application uses the current editable form values and asks where to save the filled document. Passport `{validUntil}` and residence-permit `{visaValidUntil}` are independent fields. Dates are written as `DD.MM.YYYY`.

## Running unit tests

To execute unit tests with the [Vitest](https://vitest.dev/) test runner, use the following command:

```bash
ng test
```

## Running end-to-end tests

For end-to-end (e2e) testing, run:

```bash
ng e2e
```

Angular CLI does not come with an end-to-end testing framework by default. You can choose one that suits your needs.

## Additional Resources

For more information on using the Angular CLI, including detailed command references, visit the [Angular CLI Overview and Command Reference](https://angular.dev/tools/cli) page.
