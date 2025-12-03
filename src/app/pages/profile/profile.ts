import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { AuthService } from '../../services/auth/auth';
import { ProfileService } from '../../services/profile/profile';
import { HttpClient, HttpHeaders } from '@angular/common/http';

@Component({
    selector: 'app-profile',
    standalone: true,
    imports: [CommonModule, FormsModule],
    templateUrl: './profile.html',
    styleUrls: ['./profile.css']
})
export class ProfileComponent {
    loading = true;
    error: string | null = null;
    profile: any = {
        id: null,
        email: null,
        full_name: '',
        avatar_url: null,
        firebase_uid: null,
        created_at: null,
        threads: [],
    };

    constructor(private profileSvc: ProfileService, private auth: AuthService, private router: Router, private http: HttpClient) {
        this.load();
    }

    async load() {
        this.loading = true;
        this.error = null;
        try {
            const p = await this.profileSvc.getProfile();
            if (p) this.profile = p as any;
        } catch (err: any) {
            this.error = err?.message || 'Failed to load profile';
        } finally {
            this.loading = false;
        }
    }

    async signOut() {
        await this.auth.signOut();
        this.router.navigate(['/login']);
    }
}
