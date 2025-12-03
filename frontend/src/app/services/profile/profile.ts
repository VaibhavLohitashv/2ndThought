import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { AuthService } from '../auth/auth';

@Injectable({ providedIn: 'root' })
export class ProfileService {
  private base = 'http://localhost:8000';

  constructor(private http: HttpClient, private auth: AuthService) { }

  private headers() {
    const token = this.auth.getIdToken();
    const headersConfig: { [name: string]: string } = {};
    if (token) {
      headersConfig['Authorization'] = `Bearer ${token}`;
    }
    return new HttpHeaders(headersConfig);
  }

  async getProfile() {
    const obs = this.http.get(`${this.base}/users/me`, { headers: this.headers() });
    return firstValueFrom(obs);
  }
}
