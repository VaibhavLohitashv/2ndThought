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

    show(message: string, type: Toast['type'] = 'info', duration = 4000) {
        const t: Toast = { id: String(Date.now()) + Math.random().toString(36).slice(2), message, type, duration };
        this.toastsSubject.next(t);
        return t.id;
    }
}
