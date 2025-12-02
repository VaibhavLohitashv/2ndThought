import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { AuthService } from '../auth/auth';

@Injectable({ providedIn: 'root' })
export class ThreadsService {
    private base = 'http://localhost:8000';

    constructor(private http: HttpClient, private auth: AuthService) { }

    private headers() {
        const token = this.auth.getIdToken();
        return token ? new HttpHeaders({ Authorization: `Bearer ${token}` }) : undefined;
    }

    async listThreads() {
        const obs = this.http.get(`${this.base}/threads`, { headers: this.headers() });
        return firstValueFrom(obs) as Promise<any[]>;
    }

    async createThread(data: { title: string; description?: string }) {
        const obs = this.http.post(`${this.base}/threads`, data, { headers: this.headers() });
        return firstValueFrom(obs) as Promise<any>;
    }

    async getThread(threadId: number) {
        const obs = this.http.get(`${this.base}/threads/${threadId}`, { headers: this.headers() });
        return firstValueFrom(obs) as Promise<any>;
    }
}
