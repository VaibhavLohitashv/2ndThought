import { Component } from '@angular/core';
import { Router } from '@angular/router';
import { AuthService } from '../../services/auth/auth';

@Component({
    selector: 'app-protected',
    standalone: true,
    templateUrl: './protected.html',
    styleUrls: ['./protected.css'],
    imports: []
})
export class ProtectedComponent {
    constructor(private auth: AuthService, private router: Router) { }

    async signOut() {
        await this.auth.signOut();
        this.router.navigate(['/login']);
    }
}
