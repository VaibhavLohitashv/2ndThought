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
    activeTab: 'posts' | 'create' | 'members' | 'admin' = 'posts';
    newPostContent = '';
    creatingPost = false;
    postError: string | null = null;

    // store DB user id for exact membership checks
    myUserId: number | null = null;

    // inline status messages for join/leave
    metaMessage: { type: 'success' | 'error'; text: string } | null = null;

    // leave confirmation modal state
    showLeaveConfirm = false;


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
            // fetch current user DB id for membership checks
            await this.fetchCurrentUser();
            this.thread = await this.svc.getThread(id);
            const postsRes = await this.svc.getPosts(id);
            this.posts = postsRes.posts || [];
        } catch (err) {
            console.error(err);
        } finally {
            this.loading = false;
            // if current tab requires membership but user isn't a member, switch to posts
            if (!this.isMember() && (this.activeTab === 'create' || this.activeTab === 'members')) {
                this.activeTab = 'posts';
            }
        }
    }

    // Get authoritative DB user id from backend
    async fetchCurrentUser() {
        try {
            const token = this.auth.getIdToken();
            if (!token) {
                this.myUserId = null;
                return;
            }
            const headers = { Authorization: `Bearer ${token}` };
            const obs = this.http.get(`http://localhost:8000/users/me`, { headers });
            const res = await firstValueFrom(obs) as any;
            // server returns `id` for DB user
            this.myUserId = res.id ?? null;
        } catch (err) {
            this.myUserId = null;
            console.error('Could not fetch current user', err);
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
            this.postError = err?.error?.detail ?? err?.error ?? err?.message ?? 'Could not create post';
        } finally {
            this.creatingPost = false;
        }
    }

    isMember(): boolean {
        if (!this.thread || !this.thread.members) return false;
        // if we have authoritative DB user id, match by that
        if (this.myUserId) {
            return this.thread.members.some((m: any) => m.user_id === this.myUserId);
        }
        // fallback to matching by client auth displayName/email
        const user = this.auth.user$.value;
        if (!user) return false;
        return this.thread.members.some((m: any) => {
            if (m.user_full_name && user.displayName && m.user_full_name === user.displayName) return true;
            if (m.email && user.email && m.email === user.email) return true;
            return false;
        });
    }

    async joinThread() {
        const id = Number(this.route.snapshot.paramMap.get('id'));
        if (!id) return;
        try {
            await this.svc.joinThread(id);
            // reload thread and posts
            await this.load();
            this.activeTab = 'posts';
            this.metaMessage = { type: 'success', text: 'You have joined the thread' };
            // clear message after a short delay
            setTimeout(() => (this.metaMessage = null), 4000);
        } catch (err: any) {
            console.error('join error', err);
            this.metaMessage = { type: 'error', text: err?.error?.detail ?? err?.error ?? err?.message ?? 'Could not join thread' };
            setTimeout(() => (this.metaMessage = null), 5000);
        }
    }

    // admin check: does my membership role equal 'admin' for this thread?
    isAdmin(): boolean {
        if (!this.thread || !this.thread.members) return false;
        if (this.myUserId) {
            return this.thread.members.some((m: any) => m.user_id === this.myUserId && m.role === 'admin');
        }
        // fallback - check by matching current user
        const user = this.auth.user$.value;
        if (!user) return false;
        return this.thread.members.some((m: any) => {
            if (m.role !== 'admin') return false;
            if (m.user_full_name && user.displayName && m.user_full_name === user.displayName) return true;
            if (m.email && user.email && m.email === user.email) return true;
            return false;
        });
    }

    // Promote a member through roles (calls backend /threads/{thread_id}/promote/{user_id})
    async promoteMember(userId: number) {
        const id = Number(this.route.snapshot.paramMap.get('id'));
        if (!id) return;
        // client-side guard: only admins can promote, and ignore if already moderator/admin
        if (!this.isAdmin()) {
            this.metaMessage = { type: 'error', text: 'Only admins can promote' };
            setTimeout(() => (this.metaMessage = null), 4000);
            return;
        }
        const target = this.thread?.members?.find((m: any) => m.user_id === userId);
        if (!target || target.role === 'admin') {
            this.metaMessage = { type: 'error', text: 'Cannot promote this member' };
            setTimeout(() => (this.metaMessage = null), 4000);
            return;
        }
        try {
            const res = await this.svc.promoteMember(id, userId);
            await this.load();
            const newRole = res?.role ?? 'updated';
            this.metaMessage = { type: 'success', text: `Member role updated to ${newRole}` };
            setTimeout(() => (this.metaMessage = null), 4000);
        } catch (err: any) {
            console.error('promote error', err);
            this.metaMessage = { type: 'error', text: err?.error?.detail ?? err?.error ?? err?.message ?? 'Could not promote member' };
            setTimeout(() => (this.metaMessage = null), 5000);
        }
    }

    // Demote a member through roles (calls backend /threads/{thread_id}/demote/{user_id})
    async demoteMember(userId: number) {
        const id = Number(this.route.snapshot.paramMap.get('id'));
        if (!id) return;
        // if target is an admin and we're the only admin, prevent demotion client-side
        const target = this.thread?.members?.find((m: any) => m.user_id === userId);
        if (target && target.role === 'admin') {
            const admins = (this.thread?.members || []).filter((m: any) => m.role === 'admin');
            if (admins.length <= 1) {
                this.metaMessage = { type: 'error', text: 'Cannot demote the only admin' };
                setTimeout(() => (this.metaMessage = null), 5000);
                return;
            }
        }

        try {
            const res = await this.svc.demoteMember(id, userId);
            await this.load();
            const newRole = res?.role ?? 'updated';
            this.metaMessage = { type: 'success', text: `Member role updated to ${newRole}` };
            setTimeout(() => (this.metaMessage = null), 4000);
        } catch (err: any) {
            console.error('demote error', err);
            this.metaMessage = { type: 'error', text: err?.error?.detail ?? err?.error ?? err?.message ?? 'Could not demote member' };
            setTimeout(() => (this.metaMessage = null), 5000);
        }
    }

    // return number of admins in this thread
    countAdmins(): number {
        return (this.thread?.members || []).filter((m: any) => m.role === 'admin').length;
    }
    // show leave confirmation modal
    confirmLeave() {
        this.showLeaveConfirm = true;
    }

    // user confirmed leaving
    async leaveConfirmed() {
        this.showLeaveConfirm = false;
        const id = Number(this.route.snapshot.paramMap.get('id'));
        if (!id) return;
        try {
            await this.svc.leaveThread(id);
            // reload thread and posts
            await this.load();
            this.activeTab = 'posts';
            this.metaMessage = { type: 'success', text: 'You have left the thread' };
            setTimeout(() => (this.metaMessage = null), 4000);
        } catch (err: any) {
            console.error('leave error', err);
            this.metaMessage = { type: 'error', text: err?.error?.detail ?? err?.error ?? err?.message ?? 'Could not leave thread' };
            setTimeout(() => (this.metaMessage = null), 5000);
        }
    }


}
