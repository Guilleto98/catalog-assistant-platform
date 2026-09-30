import { TestBed } from '@angular/core/testing';
import { HttpErrorResponse } from '@angular/common/http';
import { provideHttpClient } from '@angular/common/http';
import { provideRouter } from '@angular/router';
import { API_BASE_URL } from '../../core/api/config';
import { AuthService } from '../../core/auth/auth.service';
import { LoginPage } from './login.page';

describe('LoginPage', () => {
  beforeEach(() =>
    TestBed.configureTestingModule({
      imports: [LoginPage],
      providers: [
        provideRouter([]),
        provideHttpClient(),
        { provide: API_BASE_URL, useValue: '/api/v1' },
      ],
    }),
  );
  it('has labelled fields and disables invalid submit', async () => {
    const fixture = TestBed.createComponent(LoginPage);
    await fixture.whenStable();
    const element: HTMLElement = fixture.nativeElement;
    expect(element.querySelector('label[for="email"]')).not.toBeNull();
    expect(element.querySelector<HTMLButtonElement>('button[type="submit"]')?.disabled).toBe(true);
  });
  it('shows generic invalid credentials, clears password, and blocks duplicate submission', async () => {
    const fixture = TestBed.createComponent(LoginPage);
    const login = vi
      .spyOn(TestBed.inject(AuthService), 'login')
      .mockRejectedValue(new HttpErrorResponse({ status: 401 }));
    fixture.componentInstance.email = 'test@example.test';
    fixture.componentInstance.password = 'fixture-only';
    const first = fixture.componentInstance.submit();
    const second = fixture.componentInstance.submit();
    await Promise.all([first, second]);
    expect(login).toHaveBeenCalledTimes(1);
    expect(fixture.componentInstance.password).toBe('');
    expect(fixture.componentInstance.error()).toBe('El correo o la contraseña no son correctos.');
  });
  it('shows safe connection error when backend is down', async () => {
    const fixture = TestBed.createComponent(LoginPage);
    vi.spyOn(TestBed.inject(AuthService), 'login').mockRejectedValue(
      new HttpErrorResponse({ status: 0 }),
    );
    fixture.componentInstance.email = 'test@example.test';
    fixture.componentInstance.password = 'fixture-only';
    await fixture.componentInstance.submit();
    expect(fixture.componentInstance.error()).toContain('conectar');
  });
});
