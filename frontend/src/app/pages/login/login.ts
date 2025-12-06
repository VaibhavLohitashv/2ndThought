// FILE: src/app/pages/login/login.ts
import { Component } from '@angular/core';
import { Router, ActivatedRoute } from '@angular/router';
import { CommonModule } from '@angular/common';
import { AuthService } from '../../services/auth/auth';
import { LogoGeometricComponent } from '../../components/logo/logo';

@Component({
  selector: 'app-login',
  standalone: true,
  imports: [CommonModule, LogoGeometricComponent],
  templateUrl: './login.html',
  styleUrls: ['./login.css']
})
export class LoginComponent {
  loading = false;
  returnUrl = '/';

  constructor(
    private auth: AuthService,
    private router: Router,
    private route: ActivatedRoute
  ) {
    const q = this.route.snapshot.queryParamMap.get('returnUrl');
    if (q) this.returnUrl = q;
  }

  async googleSignIn() {
    this.loading = true;
    try {
      await this.auth.signInWithGoogle();
      this.router.navigateByUrl(this.returnUrl);
    } catch (err) {
      console.error(err);
    } finally {
      this.loading = false;
    }
  }
}