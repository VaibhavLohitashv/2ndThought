import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth/auth';

@Component({
    selector: 'app-protected',
    standalone: true,
    template: `
    <div style="padding:1rem">
      <h2>Protected Page</h2>
      <p>You are signed in.</p>
      <button (click)="signOut()">Sign Out</button>
    </div>
  `,
    imports: []
})
export class ProtectedComponent {
    constructor(private auth: AuthService, private router: Router) { }

    async signOut() {
        await this.auth.signOut();
        this.router.navigate(['/login']);
    }
}
