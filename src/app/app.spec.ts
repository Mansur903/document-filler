import { TestBed } from '@angular/core/testing';
import type { ComponentFixture } from '@angular/core/testing';

import type { ElectronAPI, PassportData, ResidencePermitData } from './models/api.model';
import { App } from './app';

const passportData: PassportData = {
  authority: 'FMS 12345',
  currentNationality: 'RUS',
  dateOfBirth: '1990-01-01',
  dateOfIssue: '2020-01-01',
  givenName: 'Ivan',
  issuedByCountry: 'RUS',
  numberOfTravelDocument: '123456789',
  placeOfBirth: 'Moscow',
  sex: 'M',
  surname: 'Ivanov',
  validUntil: '2030-01-01',
};
const permitData: ResidencePermitData = {
  currentOccupation: 'Engineer',
  employer: 'Example Company',
  residencepermitID: '784200910498284',
  visaID: '201/2024/3821949',
  visaValidUntil: '2027-08-28',
};

describe('App', () => {
  let electronAPI: ElectronAPI;

  beforeEach(async () => {
    electronAPI = {
      createCustomField: vi.fn().mockImplementation(async (definition) => [definition]),
      deleteCustomField: vi.fn().mockResolvedValue([]),
      generateDocument: vi.fn().mockResolvedValue(null),
      listCustomFields: vi.fn().mockResolvedValue([]),
      recognizeDocument: vi.fn().mockResolvedValue(passportData),
      resetUserSession: vi.fn().mockResolvedValue(undefined),
      selectDocumentFile: vi.fn().mockResolvedValue(null),
      selectTemplate: vi.fn().mockResolvedValue(null),
    };
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      value: electronAPI,
    });

    await TestBed.configureTestingModule({
      imports: [App],
    }).compileComponents();
  });

  it('renders the title and every form field before recognition', () => {
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('h1')?.textContent).toContain('Document Filler');
    expect(compiled.querySelectorAll('.personal-form input')).toHaveLength(19);
    expect(input(compiled, 'authority').value).toBe('');
    expect(input(compiled, 'email').value).toBe('');
    expect(input(compiled, 'address').value).toBe('');
    expect(input(compiled, 'phone').value).toBe('');
    for (const field of ['dateOfBirth', 'dateOfIssue', 'validUntil', 'visaValidUntil']) {
      expect(input(compiled, field).type).toBe('text');
      expect(input(compiled, field).getAttribute('placeholder')).toBeNull();
    }
  });

  it('shows a PNG preview returned by the Electron API', async () => {
    vi.mocked(electronAPI.selectDocumentFile).mockResolvedValue({
      name: 'permit.png',
      previewDataUrl: 'data:image/png;base64,dGVzdA==',
      type: 'image',
    });
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();

    await click(fixture, '[data-testid="select-document"]');

    const compiled = fixture.nativeElement as HTMLElement;
    expect(electronAPI.selectDocumentFile).toHaveBeenCalledOnce();
    expect(compiled.querySelector('.panel__file-name')?.textContent).toContain('permit.png');
    expect(compiled.querySelector('img')?.getAttribute('src')).toBe(
      'data:image/png;base64,dGVzdA==',
    );
  });

  it('merges passport then permit data without overwriting existing values', async () => {
    vi.mocked(electronAPI.selectDocumentFile).mockResolvedValue({
      name: 'document.png',
      previewDataUrl: 'data:image/png;base64,dGVzdA==',
      type: 'image',
    });
    vi.mocked(electronAPI.recognizeDocument).mockImplementation(async (documentType) =>
      documentType === 'passport' ? passportData : permitData,
    );
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    await click(fixture, '[data-testid="select-document"]');
    await click(fixture, '[data-testid="recognize-document"]');

    const compiled = fixture.nativeElement as HTMLElement;
    expect(input(compiled, 'authority').value).toBe('FMS 12345');
    setInput(input(compiled, 'authority'), 'Manual authority');
    setInput(input(compiled, 'email'), 'person@example.com');
    input(compiled, 'input[value="uaeResidencePermit"]')?.click();
    fixture.detectChanges();
    await click(fixture, '[data-testid="recognize-document"]');

    expect(input(compiled, 'dateOfBirth').value).toBe('01.01.1990');
    expect(input(compiled, 'dateOfIssue').value).toBe('01.01.2020');
    expect(input(compiled, 'validUntil').value).toBe('01.01.2030');
    expect(input(compiled, 'visaValidUntil').value).toBe('28.08.2027');
    expect(input(compiled, 'email').value).toBe('person@example.com');

    input(compiled, 'input[value="passport"]')?.click();
    vi.mocked(electronAPI.recognizeDocument).mockResolvedValue({
      ...passportData,
      authority: 'Replacement authority',
      surname: 'Replacement',
      validUntil: '2040-01-01',
    });
    fixture.detectChanges();
    await click(fixture, '[data-testid="recognize-document"]');

    expect(input(compiled, 'surname').value).toBe('Ivanov');
    expect(input(compiled, 'authority').value).toBe('Manual authority');
    expect(input(compiled, 'validUntil').value).toBe('01.01.2030');
  });

  it('merges permit then passport data and refills a manually cleared field', async () => {
    vi.mocked(electronAPI.selectDocumentFile).mockResolvedValue({
      name: 'document.jpg',
      previewDataUrl: 'data:image/jpeg;base64,dGVzdA==',
      type: 'image',
    });
    vi.mocked(electronAPI.recognizeDocument).mockImplementation(async (documentType) =>
      documentType === 'passport' ? passportData : permitData,
    );
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    await click(fixture, '[data-testid="select-document"]');

    const compiled = fixture.nativeElement as HTMLElement;
    input(compiled, 'input[value="uaeResidencePermit"]')?.click();
    fixture.detectChanges();
    await click(fixture, '[data-testid="recognize-document"]');
    input(compiled, 'input[value="passport"]')?.click();
    fixture.detectChanges();
    await click(fixture, '[data-testid="recognize-document"]');

    expect(input(compiled, 'visaID').value).toBe('201/2024/3821949');
    expect(input(compiled, 'surname').value).toBe('Ivanov');

    setInput(input(compiled, 'surname'), '');
    await click(fixture, '[data-testid="recognize-document"]');
    expect(input(compiled, 'surname').value).toBe('Ivanov');
  });

  it('keeps form values when file selection is replaced, cancelled, or fails', async () => {
    vi.mocked(electronAPI.selectDocumentFile)
      .mockResolvedValueOnce({
        name: 'passport.jpg',
        previewDataUrl: 'data:image/jpeg;base64,dGVzdA==',
        type: 'image',
      })
      .mockResolvedValueOnce(null)
      .mockRejectedValueOnce(new Error('failed'));
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    setInput(input(compiled, 'surname'), 'Keep me');

    await click(fixture, '[data-testid="select-document"]');
    await click(fixture, '[data-testid="select-document"]');
    await click(fixture, '[data-testid="select-document"]');

    expect(input(compiled, 'surname').value).toBe('Keep me');
    expect(compiled.querySelector('[role="alert"]')?.textContent).toContain('could not be opened');
  });

  it('confirms a populated user reset and preserves the selected template', async () => {
    vi.mocked(electronAPI.selectTemplate).mockResolvedValue({ name: 'template.docx' });
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    await click(fixture, '[data-testid="select-template"]');
    setInput(input(compiled, 'authority'), 'Manual authority');
    setInput(input(compiled, 'email'), 'person@example.com');

    await click(fixture, '[data-testid="new-user"]');
    expect(compiled.querySelector('[data-testid="confirm-new-user"]')).toBeTruthy();
    await click(fixture, '[data-testid="cancel-new-user"]');
    expect(input(compiled, 'email').value).toBe('person@example.com');

    await click(fixture, '[data-testid="new-user"]');
    await click(fixture, '[data-testid="confirm-new-user"]');

    expect(electronAPI.resetUserSession).toHaveBeenCalledOnce();
    expect(input(compiled, 'authority').value).toBe('');
    expect(input(compiled, 'email').value).toBe('');
    expect(compiled.textContent).toContain('template.docx');
  });

  it('creates a custom field, sends its value to DOCX, and removes it', async () => {
    vi.mocked(electronAPI.selectTemplate).mockResolvedValue({ name: 'template.docx' });
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;

    await click(fixture, '[data-testid="add-custom-field"]');
    const dialog = compiled.querySelector<HTMLDialogElement>('.custom-field-dialog');
    expect(dialog?.open).toBe(true);
    expect(dialog?.querySelector('input')?.getAttribute('formControlName')).toBe('label');
    setInput(input(dialog!, 'label'), 'Extra phone');
    setInput(input(dialog!, 'name'), 'extraPhone');
    await click(fixture, '.custom-field-dialog button[type="submit"]');

    expect(electronAPI.createCustomField).toHaveBeenCalledWith({
      label: 'Extra phone',
      name: 'extraPhone',
    });
    expect(compiled.textContent).toContain('{extraPhone}');
    setInput(customInput(compiled, 'extraPhone'), '12345');
    await click(fixture, '[data-testid="select-template"]');
    await click(fixture, '[data-testid="generate-document"]');
    expect(electronAPI.generateDocument).toHaveBeenCalledWith(
      expect.any(Object),
      { extraPhone: '12345' },
    );

    await click(fixture, '[data-testid="delete-custom-field-extraPhone"]');
    expect(electronAPI.deleteCustomField).toHaveBeenCalledWith('extraPhone');
    expect(compiled.querySelector('[data-testid="custom-field-extraPhone"]')).toBeNull();
  });

  it('loads saved definitions with empty values and reports invalid creation', async () => {
    vi.mocked(electronAPI.listCustomFields).mockResolvedValue([
      { label: 'Extra phone', name: 'extraPhone' },
    ]);
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(customInput(compiled, 'extraPhone').value).toBe('');

    await click(fixture, '[data-testid="add-custom-field"]');
    const dialog = compiled.querySelector<HTMLDialogElement>('.custom-field-dialog')!;
    setInput(input(dialog, 'label'), 'Duplicate');
    setInput(input(dialog, 'name'), 'EXTRAPHONE');
    await click(fixture, '.custom-field-dialog button[type="submit"]');
    expect(dialog.open).toBe(true);
    expect(dialog.textContent).toContain('already used');
    expect(electronAPI.createCustomField).not.toHaveBeenCalled();

    setInput(input(dialog, 'name'), 'bad name');
    await click(fixture, '.custom-field-dialog button[type="submit"]');
    expect(dialog.textContent).toContain('must start with a letter');
    await click(fixture, '.custom-field-dialog button[type="button"]');
    expect(dialog.open).toBe(false);
  });

  it('focuses the creation dialog and closes it with Escape', async () => {
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;

    await click(fixture, '[data-testid="add-custom-field"]');
    const dialog = compiled.querySelector<HTMLDialogElement>('.custom-field-dialog')!;
    expect(document.activeElement).toBe(input(dialog, 'label'));
    dialog.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true }));
    fixture.detectChanges();

    expect(dialog.open).toBe(false);
    expect(document.activeElement).toBe(compiled.querySelector('[data-testid="add-custom-field"]'));
    expect(electronAPI.createCustomField).not.toHaveBeenCalled();
  });

  it('keeps a field visible when deletion cannot be saved', async () => {
    vi.mocked(electronAPI.listCustomFields).mockResolvedValue([
      { label: 'Extra phone', name: 'extraPhone' },
    ]);
    vi.mocked(electronAPI.deleteCustomField).mockRejectedValue(new Error('disk full'));
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;

    await click(fixture, '[data-testid="delete-custom-field-extraPhone"]');
    expect(customInput(compiled, 'extraPhone')).toBeTruthy();
    expect(compiled.textContent).toContain('could not be deleted');
  });

  it('clears only custom values for a new user and keeps definitions', async () => {
    vi.mocked(electronAPI.listCustomFields).mockResolvedValue([
      { label: 'Extra phone', name: 'extraPhone' },
    ]);
    vi.mocked(electronAPI.selectTemplate).mockResolvedValue({ name: 'template.docx' });
    const fixture = TestBed.createComponent(App);
    fixture.detectChanges();
    await fixture.whenStable();
    fixture.detectChanges();
    const compiled = fixture.nativeElement as HTMLElement;
    await click(fixture, '[data-testid="select-template"]');
    setInput(customInput(compiled, 'extraPhone'), '12345');

    await click(fixture, '[data-testid="new-user"]');
    expect(compiled.querySelector('[data-testid="confirm-new-user"]')).toBeTruthy();
    await click(fixture, '[data-testid="cancel-new-user"]');
    expect(customInput(compiled, 'extraPhone').value).toBe('12345');
    await click(fixture, '[data-testid="new-user"]');
    await click(fixture, '[data-testid="confirm-new-user"]');

    expect(customInput(compiled, 'extraPhone').value).toBe('');
    expect(compiled.textContent).toContain('template.docx');
    expect(compiled.textContent).toContain('{extraPhone}');
  });
});

async function click(fixture: ComponentFixture<App>, selector: string): Promise<void> {
  (fixture.nativeElement as HTMLElement).querySelector<HTMLButtonElement>(selector)?.click();
  fixture.detectChanges();
  await fixture.whenStable();
  fixture.detectChanges();
}

function input(root: HTMLElement, nameOrSelector: string): HTMLInputElement {
  const selector = nameOrSelector.startsWith('input[')
    ? nameOrSelector
    : `input[formControlName="${nameOrSelector}"]`;
  const element = root.querySelector<HTMLInputElement>(selector);

  if (!element) {
    throw new Error(`Input not found: ${nameOrSelector}`);
  }

  return element;
}

function customInput(root: HTMLElement, name: string): HTMLInputElement {
  const element = root.querySelector<HTMLInputElement>(`[data-testid="custom-field-${name}"]`);

  if (!element) {
    throw new Error(`Custom input not found: ${name}`);
  }

  return element;
}

function setInput(element: HTMLInputElement, value: string): void {
  element.value = value;
  element.dispatchEvent(new Event('input'));
}
