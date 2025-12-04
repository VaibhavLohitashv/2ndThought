import { Injectable } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { AuthService } from '../auth/auth';

@Injectable({ providedIn: 'root' })
export class ThreadsService {
    private base = 'http://localhost:8000';

    // expose base for other components (useful for websocket URL construction)
    public get apiBase() {
        return this.base;
    }

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

    async searchThreads(query: string) {
        const obs = this.http.get(`${this.base}/threads/search?q=${encodeURIComponent(query)}`, { headers: this.headers() });
        return firstValueFrom(obs) as Promise<any[]>;
    }

    async getPosts(threadId: number) {
        const obs = this.http.get(`${this.base}/posts/thread/${threadId}`, { headers: this.headers() });
        return firstValueFrom(obs) as Promise<any>;
    }

    async joinThread(threadId: number) {
        const obs = this.http.post(`${this.base}/threads/${threadId}/join`, {}, { headers: this.headers() });
        return firstValueFrom(obs) as Promise<any>;
    }

    async leaveThread(threadId: number) {
        const obs = this.http.post(`${this.base}/threads/${threadId}/leave`, {}, { headers: this.headers() });
        return firstValueFrom(obs) as Promise<any>;
    }

    async promoteMember(threadId: number, userId: number) {
        const obs = this.http.post(`${this.base}/threads/${threadId}/promote/${userId}`, {}, { headers: this.headers() });
        return firstValueFrom(obs) as Promise<any>;
    }

    async demoteMember(threadId: number, userId: number) {
        const obs = this.http.post(`${this.base}/threads/${threadId}/demote/${userId}`, {}, { headers: this.headers() });
        return firstValueFrom(obs) as Promise<any>;
    }

    async replyToPost(postId: number, content: string) {
        const obs = this.http.post(`${this.base}/posts/${postId}/reply`, { content }, { headers: this.headers() });
        return firstValueFrom(obs) as Promise<any>;
    }

    async deletePost(postId: number) {
        const obs = this.http.delete(`${this.base}/posts/${postId}`, { headers: this.headers() });
        return firstValueFrom(obs) as Promise<any>;
    }
}
