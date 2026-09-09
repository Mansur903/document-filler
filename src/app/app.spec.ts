import { TestBed } from '@angular/core/testing';
import { App } from './app';

describe('App', () => {
  beforeEach(async () => {
    await TestBed.configureTestingModule({
      imports: [App],
    }).compileComponents();
  });

  it('should create the app', () => {
    const fixture = TestBed.createComponent(App);
    const app = fixture.componentInstance;
    expect(app).toBeTruthy();
  });

  it('should render title', async () => {
    const fixture = TestBed.createComponent(App);
    await fixture.whenStable();
    const compiled = fixture.nativeElement as HTMLElement;
    expect(compiled.querySelector('h1')?.textContent).toContain('Document Filler');
  });

  it('should show the image returned by the Electron API', async () => {
    const selectImage = vi.fn().mockResolvedValue({
      dataUrl: 'data:image/jpeg;base64,dGVzdA==',
      name: 'passport.jpg',
    });
    Object.defineProperty(window, 'electronAPI', {
      configurable: true,
      value: { selectImage },
    });
    const fixture = TestBed.createComponent(App);

    fixture.detectChanges();
    fixture.nativeElement.querySelector('button')?.click();
    await fixture.whenStable();
    fixture.detectChanges();

    const compiled = fixture.nativeElement as HTMLElement;
    expect(selectImage).toHaveBeenCalledOnce();
    expect(compiled.querySelector('.app-shell__file-name')?.textContent).toContain('passport.jpg');
    expect(compiled.querySelector('img')?.getAttribute('src')).toBe(
      'data:image/jpeg;base64,dGVzdA==',
    );
    expect(compiled.querySelector('button')?.textContent).toContain('Select another image');
  });
});
