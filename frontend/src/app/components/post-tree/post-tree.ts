import { Component, Input, Output, EventEmitter } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { AuthService } from '../../services/auth/auth';

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
    replyError: Record<number, string | null> = {};

    constructor(private http: HttpClient, private auth: AuthService) { }

    toggleReply(postId: number) {
        this.replyOpen[postId] = !this.replyOpen[postId];
        if (!this.replyOpen[postId]) {
            this.replyContent[postId] = '';
            this.replyError[postId] = null;
        }
    }

    async replyTo(postId: number) {
        this.replyError[postId] = null;
        this.replying[postId] = true;
        const content = (this.replyContent[postId] || '').trim();
        if (!content) {
            this.replyError[postId] = 'Reply cannot be empty';
            this.replying[postId] = false;
            return;
        }
        try {
            const token = this.auth.getIdToken();
            const headers = token ? new HttpHeaders({ Authorization: `Bearer ${token}` }) : undefined;
            const obs = this.http.post(`http://localhost:8000/posts/${postId}/reply`, { content }, { headers });
            await firstValueFrom(obs);
            this.replyContent[postId] = '';
            this.replyOpen[postId] = false;
            this.updated.emit();
        } catch (err: any) {
            console.error(err);
            this.replyError[postId] = err?.message || 'Could not post reply';
        } finally {
            this.replying[postId] = false;
        }
    }
}
