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

## Local Russian international passport OCR

Russian international passport OCR currently runs locally in development mode with Python 3.11, PaddlePaddle, and PaddleOCR.

Create the isolated environment and install the pinned dependencies:

```powershell
python -m venv .venv-ocr
.\.venv-ocr\Scripts\python.exe -m pip install -r ocr\requirements.txt
```

The OCR models are downloaded to the local PaddleX cache on first recognition. The Python runtime and models are not bundled by `package:win` yet.

## DOCX templates

Select a `.docx` template in the application after recognizing a passport. The template can contain these placeholders:

```text
{surname}
{givenName}
{dateOfBirth}
{placeOfBirth}
{currentNationality}
{sex}
{numberOfTravelDocument}
{validUntil}
{issuedByCountry}
```

The application uses the current editable form values and asks where to save the filled document. Dates are written as `DD.MM.YYYY`.

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
