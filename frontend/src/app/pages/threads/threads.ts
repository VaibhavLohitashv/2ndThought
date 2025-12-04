import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, ActivatedRoute } from '@angular/router';
import { ThreadsService } from '../../services/threads/threads';
import { CreateThreadModal } from './create-thread-modal';

@Component({
    selector: 'app-threads',
    standalone: true,
    imports: [CommonModule, CreateThreadModal],
    templateUrl: './threads.html',
    styleUrls: ['./threads.css']
})
export class ThreadsComponent {
    loading = true;
    threads: any[] = [];
    showCreate = false;

    constructor(private svc: ThreadsService, private router: Router, private route: ActivatedRoute) {
        // react to query param changes (e.g. ?search=...)
        this.route.queryParams.subscribe((qp) => {
            const q = qp['search'];
            this.load(q);
        });
    }

    async load(searchQuery?: string) {
        this.loading = true;
        try {
            if (searchQuery && searchQuery.trim()) {
                this.threads = await this.svc.searchThreads(searchQuery);
            } else {
                this.threads = await this.svc.listThreads();
            }
        } catch (err) {
            console.error(err);
        } finally {
            this.loading = false;
        }
    }

    openThread(id: number) {
        this.router.navigate([`/threads/${id}`]);
    }

    openCreate() {
        this.showCreate = true;
    }

    onCreated() {
        this.showCreate = false;
        this.load();
    }

    onClose() {
        this.showCreate = false;
    }
}
