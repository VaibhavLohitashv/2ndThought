import { Component, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ToastService, Toast } from '../../services/toast/toast';
import { Subscription, timer } from 'rxjs';

@Component({
    selector: 'app-toasts',
    standalone: true,
    imports: [CommonModule],
    templateUrl: './toast.html',
    styleUrls: ['./toast.css']
})
export class ToastComponent implements OnDestroy {
    toasts: Toast[] = [];
    subs = new Subscription();

    constructor(private svc: ToastService) {
        this.subs.add(
            this.svc.toasts$.subscribe((t) => {
                this.toasts = [t, ...this.toasts];
                const d = t.duration ?? 4000;
                const s = timer(d).subscribe(() => {
                    this.removeToast(t.id);
                    s.unsubscribe();
                });
            })
        );
    }

    removeToast(id: string) {
        this.toasts = this.toasts.filter((x) => x.id !== id);
    }

    ngOnDestroy(): void {
        this.subs.unsubscribe();
    }
}
