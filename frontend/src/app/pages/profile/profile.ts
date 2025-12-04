import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { AuthService } from '../../services/auth/auth';
import { ProfileService } from '../../services/profile/profile';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { ToastService } from '../../services/toast/toast';

@Component({
    selector: 'app-profile',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './profile.html',
    styleUrls: ['./profile.css']
})
export class ProfileComponent {
    loading = true;

    profile: any = {
        id: null,
        email: null,
        full_name: '',
        avatar_url: null,
        firebase_uid: null,
        created_at: null,
        threads: [],
    };
    avatarSrc: string | null = null;

    constructor(private profileSvc: ProfileService, private auth: AuthService, private router: Router, private http: HttpClient, private toast: ToastService) {
        this.load();
    }

    async load() {
        this.loading = true;
        try {
            const p = await this.profileSvc.getProfile();
            if (p) this.profile = p as any;
            // set avatarSrc only once (avoid repeated reassignments)
            if (!this.avatarSrc && this.profile?.avatar_url) {
                this.avatarSrc = this.profile.avatar_url;
            }
        } catch (err: any) {
            const msg = err?.message || 'Failed to load profile';
            this.toast.show(msg, 'error', 5000);
        } finally {
            this.loading = false;
        }
    }

    async signOut() {
        await this.auth.signOut();
        this.router.navigate(['/login']);
    }

    onAvatarError() {
        // avoid retry loops by clearing avatarSrc so template shows initials
        this.avatarSrc = null;
    }
}
