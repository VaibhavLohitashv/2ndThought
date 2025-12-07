import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { firstValueFrom } from 'rxjs';
import { AuthService } from '../../services/auth/auth';
import { ThreadsService } from '../../services/threads/threads';
import { ToastService } from '../../services/toast/toast';

@Component({
    selector: 'app-post-tree',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './post-tree.html',
    styleUrls: ['./post-tree.css'],
})
export class PostTree {
    @Input() posts: any[] = [];
    @Input() threadMembers: any[] = [];
    @Input() myUserId: number | null = null;
    @Output() updated = new EventEmitter<void>();
    @Output() typing = new EventEmitter<void>();

    // local reply state
    replyOpen: Record<number, boolean> = {};
    replyContent: Record<number, string> = {};
    replyImage: Record<number, File | null> = {};
    replying: Record<number, boolean> = {};

    constructor(private svc: ThreadsService, private auth: AuthService, private toast: ToastService) { }

    canDelete(post: any): boolean {
        // prefer authoritative DB user id passed from parent
        if (this.myUserId) {
            // owner
            if (post.user && post.user.id && post.user.id === this.myUserId) return true;
            // membership-based admin/moderator check
            if (this.threadMembers && Array.isArray(this.threadMembers)) {
                const me = this.threadMembers.find((m: any) => m.user_id === this.myUserId);
                if (me && (me.role === 'admin' || me.role === 'moderator')) return true;
            }
            return false;
        }

        // fallback: attempt to infer from auth user (best-effort only)
        const user = this.auth.user$.value;
        if (!user) return false;
        if (post.user && post.user.id && user.uid && post.user.id === (user['dbId'] || null)) return true;
        return false;
    }

    canReply(): boolean {
        // check if current user is a member of the thread
        if (this.myUserId && this.threadMembers && Array.isArray(this.threadMembers)) {
            return this.threadMembers.some((m: any) => m.user_id === this.myUserId);
        }
        return false;
    }

    toggleReply(postId: number) {
        this.replyOpen[postId] = !this.replyOpen[postId];
        if (!this.replyOpen[postId]) {
            this.replyContent[postId] = '';
            this.replyImage[postId] = null;
        }
    }

    async replyTo(postId: number) {
        this.replying[postId] = true;
        const content = (this.replyContent[postId] || '').trim();
        if (!content) {
            this.toast.show('Reply cannot be empty', 'warning', 3000);
            this.replying[postId] = false;
            return;
        }
        try {
            await this.svc.replyToPost(postId, content, this.replyImage[postId] || undefined);
            this.replyContent[postId] = '';
            this.replyImage[postId] = null;
            this.replyOpen[postId] = false;
            this.updated.emit();
        } catch (err: any) {
            console.error(err);
            this.toast.show(err?.message || 'Could not post reply', 'error', 5000);
        } finally {
            this.replying[postId] = false;
        }
    }

    onReplyFileSelected(postId: number, event: any) {
        const file = event.target.files[0];
        if (file) {
            this.replyImage[postId] = file;
        }
    }

    removeReplyImage(postId: number) {
        this.replyImage[postId] = null;
    }

    // delete a post (admin or owner allowed)
    async deletePost(postId: number) {
        // optimistic removal from UI
        const removeFromList = (list: any[]) => {
            for (let i = list.length - 1; i >= 0; i--) {
                const p = list[i];
                if (p.id === postId) {
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
        try {
            await this.svc.deletePost(postId);
            this.toast.show('Post deleted', 'success', 3000);
        } catch (err: any) {
            console.error('delete error', err);
            this.toast.show(err?.message || 'Could not delete post', 'error', 5000);
            if (!found) {
                // if we didn't remove it, attempt reload
                this.updated.emit();
            }
        }
    }
}
