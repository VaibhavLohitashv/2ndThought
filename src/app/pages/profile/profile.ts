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
    template: `
        <div style="padding:1rem; max-width:800px">
            <h2>Profile</h2>
            <div *ngIf="loading">Loading...</div>

            <div *ngIf="!loading">
                <div style="display:flex; gap:1rem; align-items:center">
                    <img *ngIf="profile.avatar_url" [src]="profile.avatar_url" alt="avatar" width="96" height="96" style="border-radius:8px; object-fit:cover" />
                    <div>
                        <div><strong>Email:</strong> {{ profile.email || '-' }}</div>
                        <div><strong>Firebase UID:</strong> {{ profile.firebase_uid || '-' }}</div>
                        <div><strong>Joined:</strong> {{ profile.created_at | date:'medium' }}</div>
                    </div>
                </div>

                <form style="margin-top:1rem" (ngSubmit)="save()">
                    <label>
                        Full name
                        <input [(ngModel)]="profile.full_name" name="full_name" />
                    </label>
                    <br />
                    <label>
                        Avatar URL
                        <input [(ngModel)]="profile.avatar_url" name="avatar_url" />
                    </label>
                    <br />
                    <button type="submit">Save</button>
                    <button type="button" (click)="signOut()">Sign Out</button>
                </form>

                <section style="margin-top:1.25rem">
                    <h3>Threads</h3>
                    <div *ngIf="!profile.threads || profile.threads.length === 0">You haven't joined any threads yet.</div>
                    <ul>
                        <li *ngFor="let t of profile.threads">
                            <strong>{{ t.thread_title }}</strong> — <em>{{ t.role }}</em>
                            <div style="font-size:0.9rem; color:gray">Joined: {{ t.joined_at | date:'medium' }}</div>
                        </li>
                    </ul>
                </section>

                <div *ngIf="error" style="color:tomato; margin-top:0.5rem">{{ error }}</div>
            </div>
        </div>
  `
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

    async save() {
        this.loading = true;
        this.error = null;
        try {
            const token = this.auth.getIdToken();
            const headers = token ? new HttpHeaders({ Authorization: `Bearer ${token}` }) : undefined;
            await firstValueFrom(this.http.put(`http://localhost:8000/users/me`, {
                full_name: this.profile.full_name,
                avatar_url: this.profile.avatar_url,
            }, { headers }));
            await this.load();
        } catch (err: any) {
            this.error = err?.message || 'Failed to save profile';
        } finally {
            this.loading = false;
        }
    }

    async signOut() {
        await this.auth.signOut();
        this.router.navigate(['/login']);
    }
}
