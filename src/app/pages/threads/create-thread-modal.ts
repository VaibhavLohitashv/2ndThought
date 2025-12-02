import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ThreadsService } from '../../services/threads/threads';

@Component({
    selector: 'app-create-thread-modal',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './create-thread-modal.html',
    styleUrls: ['./create-thread-modal.css']
})
export class CreateThreadModal {
    title = '';
    description = '';
    loading = false;
    error: string | null = null;

    @Output() created = new EventEmitter<void>();
    @Output() closed = new EventEmitter<void>();

    constructor(private svc: ThreadsService) { }

    async submit() {
        this.loading = true;
        this.error = null;
        try {
            await this.svc.createThread({ title: this.title, description: this.description });
            this.created.emit();
        } catch (err: any) {
            this.error = err?.message || 'Could not create thread';
        } finally {
            this.loading = false;
        }
    }

    close() {
        this.closed.emit();
    }
}
