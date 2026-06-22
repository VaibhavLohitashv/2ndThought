import { Injectable } from '@angular/core';
import { Subject, Observable } from 'rxjs';

export interface Toast {
    id: string;
    message: string;
    type?: 'info' | 'success' | 'warning' | 'error';
    duration?: number;
}

@Injectable({ providedIn: 'root' })
export class ToastService {
    private toastsSubject = new Subject<Toast>();
    public toasts$: Observable<Toast> = this.toastsSubject.asObservable();
    private counter = 0;

    show(message: string, type: Toast['type'] = 'info', duration = 4000) {
        // SECURITY: Use monotonic counter instead of Math.random() for toast IDs to avoid weak PRNG
        const t: Toast = { id: `${Date.now()}-${++this.counter}`, message, type, duration };
        this.toastsSubject.next(t);
        return t.id;
    }
}