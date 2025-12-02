import { Component } from '@angular/core';
import { Router, ActivatedRoute } from '@angular/router';
import { AuthService } from '../../services/auth/auth';

@Component({
  selector: 'app-login',
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
