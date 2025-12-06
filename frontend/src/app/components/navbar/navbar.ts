// FILE: src/app/components/navbar/navbar.ts
import { Component, OnDestroy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../services/auth/auth';
import { ThreadsService } from '../../services/threads/threads';
import { ToastService } from '../../services/toast/toast';
import { LogoGeometricComponent } from '../logo/logo';

interface NotificationItem {
    type: string;
    message: string;
    thread_id?: number;
}

@Component({
    selector: 'app-navbar',
    standalone: true,
    imports: [CommonModule, FormsModule, RouterLink, LogoGeometricComponent],
    templateUrl: './navbar.html',
    styleUrls: ['./navbar.css']
})
export class NavbarComponent implements OnDestroy {
    query = '';
    notifications: NotificationItem[] = [];
    ws: WebSocket | null = null;
    unreadCount = 0;
    notifOpen = false;

    constructor(
        public auth: AuthService,
        public router: Router,
        private svc: ThreadsService,
        private toast: ToastService
    ) {
        this.auth.user$.subscribe((u) => {
            if (u) {
                this.connectNotifications();
            } else {
                this.disconnectNotifications();
                this.notifications = [];
                this.unreadCount = 0;
            }
        });
    }

    ngOnDestroy(): void {
        this.disconnectNotifications();
    }

    onSearch() {
        const q = (this.query || '').trim();
        this.router.navigate(['/threads'], { queryParams: { search: q } });
    }

    toggleNotifications() {
        this.notifOpen = !this.notifOpen;
        if (this.notifOpen) this.unreadCount = 0;
    }

    getInitials(user: any) {
        if (!user) return '';
        const name = user.full_name || user.email || '';
        const parts = name.trim().split(/\s+/).filter(Boolean);
        if (parts.length === 0) return '';
        if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
        return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
    }

    private connectNotifications() {
        if (this.ws) return;
        const token = this.auth.getIdToken();
        if (!token) return;
        const base = this.svc.apiBase.replace(/^http/, location.protocol === 'https:' ? 'wss' : 'ws');
        const url = `${base.replace(/\/$/, '')}/ws/notifications?token=${token}`;
        try {
            this.ws = new WebSocket(url);
        } catch (e) {
            console.error('notif ws ctor', e);
            return;
        }
        this.ws.onmessage = (ev) => {
            try {
                const msg = JSON.parse(ev.data) as NotificationItem;
                this.notifications.unshift(msg);
                this.unreadCount += 1;
            } catch (e) {
                console.error('invalid notif', e);
                this.toast.show('Received invalid notification payload', 'warning');
            }
        };
        this.ws.onopen = () => console.log('notif ws open');
        this.ws.onclose = () => { this.ws = null; };
        this.ws.onerror = (e) => {
            console.error('notif ws error', e);
            this.toast.show('Notification connection error', 'error');
            try { this.ws?.close(); } catch { }
        };
    }

    private disconnectNotifications() {
        if (this.ws) {
            try { this.ws.close(); } catch { }
            this.ws = null;
        }
    }

    goProfile() {
        this.router.navigate(['/profile']);
    }

    logout() {
        this.auth.signOut();
    }

    login() {
        this.router.navigate(['/login']);
    }
}