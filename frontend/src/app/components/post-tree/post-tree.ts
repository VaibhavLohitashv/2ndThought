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
    @Output() updated = new EventEmitter<void>();

    // local reply state
    replyOpen: Record<number, boolean> = {};
    replyContent: Record<number, string> = {};
    replying: Record<number, boolean> = {};

    constructor(private svc: ThreadsService, private auth: AuthService, private toast: ToastService) { }

    toggleReply(postId: number) {
        this.replyOpen[postId] = !this.replyOpen[postId];
        if (!this.replyOpen[postId]) {
            this.replyContent[postId] = '';
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
            await this.svc.replyToPost(postId, content);
            this.replyContent[postId] = '';
            this.replyOpen[postId] = false;
            this.updated.emit();
        } catch (err: any) {
            console.error(err);
            this.toast.show(err?.message || 'Could not post reply', 'error', 5000);
        } finally {
            this.replying[postId] = false;
        }
    }
}
