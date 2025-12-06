import { Component, ChangeDetectorRef } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { ThreadsService } from '../../services/threads/threads';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { AuthService } from '../../services/auth/auth';
import { ToastService } from '../../services/toast/toast';
import { PostTree } from '../../components/post-tree/post-tree';
import { OnDestroy } from '@angular/core';

@Component({
    selector: 'app-thread-detail',
    standalone: true,
    imports: [CommonModule, FormsModule, PostTree],
    templateUrl: './thread-detail.html',
    styleUrls: ['./thread-detail.css'],
})
export class ThreadDetail implements OnDestroy {
    loading = true;
    thread: any = null;
    posts: any[] = [];
    activeTab: 'posts' | 'create' | 'members' | 'admin' = 'posts';
    newPostContent = '';
    creatingPost = false;

    // store DB user id for exact membership checks
    myUserId: number | null = null;

    // leave confirmation modal state
    showLeaveConfirm = false;

    // websocket
    private ws: WebSocket | null = null;
    private reconnectTimer: any = null;
    // typing indicator state
    typingUsers: Record<number, string> = {};
    private typingTimeouts: Record<number, any> = {};


    constructor(
        private route: ActivatedRoute,
        private router: Router,
        private svc: ThreadsService,
        private http: HttpClient,
        private auth: AuthService,
        private toast: ToastService,
        private cdr: ChangeDetectorRef
    ) {
        this.auth.user$.subscribe((u) => {
            // trigger UI update when auth changes
        });
        this.load();
    }

    ngOnDestroy(): void {
        this.disconnectWS();
    }

    // expose token for template use via a public getter
    public get idToken(): string | null {
        return this.auth.getIdToken();
    }

    // getter for typing users keys (for template)
    public get typingUserKeys(): number[] {
        return Object.keys(this.typingUsers).map(k => Number(k));
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
        // (re)connect websocket for this thread
        this.connectWS(id).catch((e) => console.error('ws connect error', e));
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
        this.creatingPost = true;
        const id = Number(this.route.snapshot.paramMap.get('id'));
        if (!id) {
            this.toast.show('Invalid thread id', 'error', 4000);
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
            const msg = err?.error?.detail ?? err?.error ?? err?.message ?? 'Could not create post';
            this.toast.show(msg ?? 'An unknown error occurred', 'error', 5000);
        } finally {
            this.creatingPost = false;
        }
    }

    // called by template on input in create textarea
    onCreateInput() {
        if (!this.ws) return;
        try {
            this.ws.send(JSON.stringify({ type: 'typing' }));
        } catch (e) { }
        // also schedule stop event after short idle
        this.scheduleLocalTypingStop();
    }

    // called when typing in reply textareas (from post-tree component)
    onReplyTyping() {
        if (!this.ws) return;
        try {
            this.ws.send(JSON.stringify({ type: 'typing' }));
        } catch (e) { }
        // also schedule stop event after short idle
        this.scheduleLocalTypingStop();
    }

    private scheduleLocalTypingStop() {
        // send typing_stop after 3s of inactivity
        if (this.typingTimeouts[-1]) {
            clearTimeout(this.typingTimeouts[-1]);
        }
        this.typingTimeouts[-1] = setTimeout(() => {
            try { this.ws?.send(JSON.stringify({ type: 'typing_stop' })); } catch (e) { }
        }, 3000);
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
            this.toast.show('You have joined the thread', 'success', 4000);
        } catch (err: any) {
            console.error('join error', err);
            this.toast.show(err?.error?.detail ?? err?.error ?? err?.message ?? 'Could not join thread', 'error', 5000);
        }
    }

    // WebSocket helpers
    private async connectWS(threadId: number) {
        this.disconnectWS();
        const token = this.auth.getIdToken();
        if (!token) return;
        // use backend base URL from ThreadsService
        const base = this.svc.apiBase.replace(/^http/, location.protocol === 'https:' ? 'wss' : 'ws');
        const url = `${base.replace(/\/$/, '')}/ws/thread/${threadId}?token=${token}`;
        try {
            this.ws = new WebSocket(url);
        } catch (e) {
            console.error('ws ctor failed', e);
            return;
        }

        this.ws.onopen = () => {
            console.log('ws open for thread', threadId);
            if (this.reconnectTimer) {
                clearTimeout(this.reconnectTimer);
                this.reconnectTimer = null;
            }
        };

        this.ws.onmessage = (ev) => {
            try {
                const msg = JSON.parse(ev.data);
                this.handleWSMessage(msg);
            } catch (e) {
                console.error('invalid ws message', e);
            }
        };

        this.ws.onclose = () => {
            console.log('ws closed, scheduling reconnect');
            this.ws = null;
            // attempt reconnect in a few seconds
            this.reconnectTimer = setTimeout(() => this.connectWS(threadId), 3000);
        };

        this.ws.onerror = (e) => {
            console.error('ws error', e);
            try {
                this.ws?.close();
            } catch { }
        };
    }

    private disconnectWS() {
        if (this.reconnectTimer) {
            clearTimeout(this.reconnectTimer);
            this.reconnectTimer = null;
        }
        if (this.ws) {
            try {
                this.ws.close();
            } catch { }
            this.ws = null;
        }
        // clear all typing timeouts and indicators
        Object.values(this.typingTimeouts).forEach(timeout => clearTimeout(timeout));
        this.typingTimeouts = {};
        this.typingUsers = {};
    }

    private handleWSMessage(msg: any) {
        if (!msg || !msg.type) return;
        if (msg.type === 'post_created' && msg.post) {
            // prepend new post
            const p = msg.post;
            p._highlight = true;
            this.posts = [p, ...this.posts];
            this.toast.show('New post in thread', 'info', 3500);
            setTimeout(() => (p._highlight = false), 3000);
        } else if (msg.type === 'reply_created' && msg.post) {
            // find parent and insert into children
            const parentId = msg.post.parent_id;
            const insertReply = (list: any[]) => {
                for (const p of list) {
                    if (p.id === parentId) {
                        p.children = p.children || [];
                        p.children.push(msg.post);
                        return true;
                    }
                    if (p.children && p.children.length) {
                        if (insertReply(p.children)) return true;
                    }
                }
                return false;
            };
            // try to insert; if not found, reload
            const found = insertReply(this.posts);
            if (found) {
                this.toast.show('New reply', 'info', 3000);
            } else {
                this.load();
                this.toast.show('New reply (reloaded)', 'info', 3000);
            }
        }
        else if (msg.type === 'post_deleted' && msg.post_id) {
            // remove the post (and its subtree) from local posts
            const removeId = msg.post_id;
            const removeFromList = (list: any[]) => {
                for (let i = list.length - 1; i >= 0; i--) {
                    const p = list[i];
                    if (p.id === removeId) {
                        list.splice(i, 1);
                        return true;
                    }
                    if (p.children && p.children.length) {
                        if (removeFromList(p.children)) return true;
                    }
                }
                return false;
            };
            const found = removeFromList(this.posts);
            if (found) {
                this.toast.show('A post was deleted', 'info', 3000);
            } else {
                // if not found, reload to be safe
                this.load();
                this.toast.show('A post was deleted (reloaded)', 'info', 3000);
            }
        } else if (msg.type === 'posts_deleted' && msg.post_ids && Array.isArray(msg.post_ids)) {
            // remove multiple post ids
            const ids = new Set(msg.post_ids);
            const removeFromListMultiple = (list: any[]) => {
                for (let i = list.length - 1; i >= 0; i--) {
                    const p = list[i];
                    if (ids.has(p.id)) {
                        list.splice(i, 1);
                        continue;
                    }
                    if (p.children && p.children.length) removeFromListMultiple(p.children);
                }
            };
            removeFromListMultiple(this.posts);
            this.toast.show('Posts were deleted', 'info', 3000);
        } else if (msg.type === 'typing' && msg.user) {
            // add user to typing indicators (exclude self)
            if (msg.user.id !== this.myUserId) {
                this.typingUsers = { ...this.typingUsers, [msg.user.id]: msg.user.full_name || `User ${msg.user.id}` };
                // clear any existing timeout for this user
                if (this.typingTimeouts[msg.user.id]) {
                    clearTimeout(this.typingTimeouts[msg.user.id]);
                }
                // auto-remove after 5s if no stop received
                this.typingTimeouts[msg.user.id] = setTimeout(() => {
                    const newTypingUsers = { ...this.typingUsers };
                    delete newTypingUsers[msg.user.id];
                    this.typingUsers = newTypingUsers;
                    delete this.typingTimeouts[msg.user.id];
                }, 5000);
            }
        } else if (msg.type === 'typing_stop' && msg.user) {
            // remove user from typing indicators
            const newTypingUsers = { ...this.typingUsers };
            delete newTypingUsers[msg.user.id];
            this.typingUsers = newTypingUsers;
            if (this.typingTimeouts[msg.user.id]) {
                clearTimeout(this.typingTimeouts[msg.user.id]);
                delete this.typingTimeouts[msg.user.id];
            }
        } else if (msg.type === 'role_updated' && msg.user_id && msg.new_role) {
            // Update the role of the user in the thread members list
            const member = this.thread?.members?.find((m: any) => m.user_id === msg.user_id);
            if (member) {
                member.role = msg.new_role;
                this.updateUIForRoleChange(member.user_id, msg.new_role);
                this.toast.show(`User role updated to ${msg.new_role}`, 'info', 3500);
            }
        }
    }

    private updateUIForRoleChange(userId: number, newRole: string) {
        // Trigger change detection to update the UI dynamically for the role change
        this.cdr.detectChanges();
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
            this.toast.show('Only admins can promote', 'error', 4000);
            return;
        }
        const target = this.thread?.members?.find((m: any) => m.user_id === userId);
        if (!target || target.role === 'admin') {
            this.toast.show('Cannot promote this member', 'error', 4000);
            return;
        }
        try {
            const res = await this.svc.promoteMember(id, userId);
            await this.load();
            const newRole = res?.role ?? 'updated';
            this.toast.show(`Member role updated to ${newRole}`, 'success', 4000);
        } catch (err: any) {
            console.error('promote error', err);
            this.toast.show(err?.error?.detail ?? err?.error ?? err?.message ?? 'Could not promote member', 'error', 5000);
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
                this.toast.show('Cannot demote the only admin', 'error', 5000);
                return;
            }
        }

        try {
            const res = await this.svc.demoteMember(id, userId);
            await this.load();
            const newRole = res?.role ?? 'updated';
            this.toast.show(`Member role updated to ${newRole}`, 'success', 4000);
        } catch (err: any) {
            console.error('demote error', err);
            this.toast.show(err?.error?.detail ?? err?.error ?? err?.message ?? 'Could not demote member', 'error', 5000);
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

    selectTab(tab: 'posts' | 'create' | 'members' | 'admin') {
        if (tab === 'admin' && !this.isAdmin()) {
            this.toast.show('Only thread admins can view this panel.', 'error', 4000);
            return;
        }
        this.activeTab = tab;
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
            this.toast.show('You have left the thread', 'success', 4000);
        } catch (err: any) {
            console.error('leave error', err);
            this.toast.show(err?.error?.detail ?? err?.error ?? err?.message ?? 'Could not leave thread', 'error', 5000);
        }
    }

    getUserRole(): string {
        return this.thread?.members?.find((m: any) => m.user_id === this.myUserId)?.role || 'N/A';
    }
}