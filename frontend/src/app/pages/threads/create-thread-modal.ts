import { Component, EventEmitter, Output } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ThreadsService } from '../../services/threads/threads';
import { ToastService } from '../../services/toast/toast';

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


    @Output() created = new EventEmitter<void>();
    @Output() closed = new EventEmitter<void>();

    constructor(private svc: ThreadsService, private toast: ToastService) { }

    async submit() {
        this.loading = true;

        try {
            await this.svc.createThread({ title: this.title, description: this.description });
            this.created.emit();
        } catch (err: any) {
            const msg = err?.message || 'Could not create thread';
            this.toast.show(msg, 'error', 5000);
        } finally {
            this.loading = false;
        }
    }

    close() {
        this.closed.emit();
    }
}
