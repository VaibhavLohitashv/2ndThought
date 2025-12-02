import { Routes } from '@angular/router';
import { LoginComponent } from './pages/login/login';
import { AuthGuard } from './guards/auth/auth-guard';
import { importProvidersFrom } from '@angular/core';
import { AngularFireModule } from '@angular/fire/compat';
import { AngularFireAuthModule } from '@angular/fire/compat/auth';
import { HttpClientModule } from '@angular/common/http';
import { environment } from '../environments/environment';

export const routes: Routes = [
    { path: 'login', component: LoginComponent },
    {
        path: 'protected',
        canActivate: [AuthGuard],
        loadComponent: () => import('./pages/protected/protected').then(m => m.ProtectedComponent)
    },
    {
        path: 'profile',
        canActivate: [AuthGuard],
        loadComponent: () => import('./pages/profile/profile').then(m => m.ProfileComponent)
    },
    { path: '', redirectTo: 'protected', pathMatch: 'full' },
];

export const routerProviders = [
    importProvidersFrom(AngularFireModule.initializeApp(environment.firebase)),
    importProvidersFrom(AngularFireAuthModule),
    importProvidersFrom(HttpClientModule)
];
