import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { ThreadsService } from '../../services/threads/threads';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { AuthService } from '../../services/auth/auth';
import { PostTree } from '../../components/post-tree/post-tree';

@Component({
    selector: 'app-thread-detail',
    standalone: true,
    imports: [CommonModule, FormsModule, PostTree],
    templateUrl: './thread-detail.html',
    styleUrls: ['./thread-detail.css'],
})
export class ThreadDetail {
    loading = true;
    thread: any = null;
    posts: any[] = [];
    activeTab: 'posts' | 'create' | 'members' = 'posts';
    newPostContent = '';
    creatingPost = false;
    postError: string | null = null;


    constructor(
        private route: ActivatedRoute,
        private router: Router,
        private svc: ThreadsService,
        private http: HttpClient,
        private auth: AuthService
    ) {
        this.auth.user$.subscribe((u) => {
            // trigger UI update when auth changes
        });
        this.load();
    }

    // expose token for template use via a public getter
    public get idToken(): string | null {
        return this.auth.getIdToken();
    }

    async load() {
        this.loading = true;
        const id = Number(this.route.snapshot.paramMap.get('id'));
        if (!id) {
            this.router.navigate(['/threads']);
            return;
        }
        try {
            this.thread = await this.svc.getThread(id);
            const postsObs = this.http.get(`http://localhost:8000/posts/thread/${id}`);
            const res = await firstValueFrom(postsObs) as any;
            this.posts = res.posts || [];
        } catch (err) {
            console.error(err);
        } finally {
            this.loading = false;
        }
    }

    back() {
        this.router.navigate(['/threads']);
    }

    async createPost() {
        this.postError = null;
        this.creatingPost = true;
        const id = Number(this.route.snapshot.paramMap.get('id'));
        if (!id) {
            this.postError = 'Invalid thread id';
            this.creatingPost = false;
            return;
        }
        try {
            const token = this.auth.getIdToken();
            const headers = token ? new HttpHeaders({ Authorization: `Bearer ${token}` }) : undefined;
            const obs = this.http.post(`http://localhost:8000/posts`, { thread_id: id, content: this.newPostContent }, { headers });
            await firstValueFrom(obs);
            this.newPostContent = '';
            // reload posts and switch to posts tab
            await this.load();
            this.activeTab = 'posts';
        } catch (err: any) {
            console.error(err);
            this.postError = err?.message || 'Could not create post';
        } finally {
            this.creatingPost = false;
        }
    }

    isMember(): boolean {
        if (!this.thread || !this.thread.members) return false;
        const user = this.auth.user$.value;
        if (!user) return false;
        // try to match by email or displayName
        return this.thread.members.some((m: any) => {
            if (m.user_full_name && user.displayName && m.user_full_name === user.displayName) return true;
            if (m.email && user.email && m.email === user.email) return true;
            // fallback: if server populated email in members (unlikely), match
            return false;
        });
    }

    async joinThread() {
        const id = Number(this.route.snapshot.paramMap.get('id'));
        if (!id) return;
        try {
            const token = this.auth.getIdToken();
            const headers = token ? new HttpHeaders({ Authorization: `Bearer ${token}` }) : undefined;
            const obs = this.http.post(`http://localhost:8000/threads/${id}/join`, {}, { headers });
            await firstValueFrom(obs);
            // reload thread and posts
            await this.load();
            this.activeTab = 'posts';
        } catch (err: any) {
            console.error('join error', err);
        }
    }


}
