import { Component } from '@angular/core';
import { CommonModule } from '@angular/common';
import { Router, RouterLink, RouterLinkActive } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { AuthService } from '../../services/auth/auth';

@Component({
    selector: 'app-navbar',
    standalone: true,
    imports: [CommonModule, FormsModule, RouterLink],
    templateUrl: './navbar.html',
    styleUrls: ['./navbar.css']
})
export class NavbarComponent {
    query = '';

    constructor(public auth: AuthService, private router: Router) { }

    onSearch() {
        // currently just logs and could navigate to a search results page later
        console.log('search for', this.query);
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
