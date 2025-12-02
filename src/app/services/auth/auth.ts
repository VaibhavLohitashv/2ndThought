import { Injectable } from '@angular/core';
import { Router } from '@angular/router';
import { AngularFireAuth } from '@angular/fire/compat/auth';
import firebase from 'firebase/compat/app';
import 'firebase/compat/auth';
import { BehaviorSubject } from 'rxjs';

@Injectable({
  providedIn: 'root',
})
export class AuthService {
  public user$ = new BehaviorSubject<any>(null);

  constructor(private afAuth: AngularFireAuth, private router: Router) {
    this.afAuth.authState.subscribe((u) => {
      this.user$.next(u);
      if (u) {
        u.getIdToken().then((t) => localStorage.setItem('idToken', t));
      } else {
        localStorage.removeItem('idToken');
      }
    });
  }

  async signInWithGoogle() {
    const provider = new firebase.auth.GoogleAuthProvider();
    const cred = await this.afAuth.signInWithPopup(provider);
    const user = cred.user;
    if (user) {
      const token = await user.getIdToken();
      localStorage.setItem('idToken', token);
      this.user$.next(user);
    }
    return cred;
  }

  async signOut() {
    await this.afAuth.signOut();
    localStorage.removeItem('idToken');
    this.user$.next(null);
    this.router.navigate(['/login']);
  }

  getIdToken(): string | null {
    return localStorage.getItem('idToken');
  }
}
