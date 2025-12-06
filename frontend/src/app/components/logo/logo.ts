// FILE: src/app/components/logo/logo-geometric.ts
import { Component, Input } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
    selector: 'app-logo-geometric',
    standalone: true,
    imports: [CommonModule],
    template: `
        <svg 
            [attr.width]="size" 
            [attr.height]="size" 
            viewBox="0 0 48 48" 
            fill="none" 
            xmlns="http://www.w3.org/2000/svg"
            class="logo"
        >
            <defs>
                <linearGradient id="logoGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#60a5fa"/>
                    <stop offset="50%" stop-color="#3b82f6"/>
                    <stop offset="100%" stop-color="#2563eb"/>
                </linearGradient>
                <linearGradient id="logoGradDark" x1="0%" y1="0%" x2="100%" y2="100%">
                    <stop offset="0%" stop-color="#3b82f6"/>
                    <stop offset="100%" stop-color="#1d4ed8"/>
                </linearGradient>
                <filter id="glow" x="-50%" y="-50%" width="200%" height="200%">
                    <feGaussianBlur stdDeviation="2" result="blur"/>
                    <feMerge>
                        <feMergeNode in="blur"/>
                        <feMergeNode in="SourceGraphic"/>
                    </feMerge>
                </filter>
                <filter id="shadowGlow" x="-50%" y="-50%" width="200%" height="200%">
                    <feDropShadow dx="0" dy="4" stdDeviation="4" flood-color="#3b82f6" flood-opacity="0.4"/>
                </filter>
            </defs>
            
            <!-- Background -->
            <rect 
                x="2" y="2" 
                width="44" height="44" 
                rx="14" 
                fill="url(#logoGrad)"
                filter="url(#shadowGlow)"
                class="logo-bg"
            />
            
            <!-- Inner highlight -->
            <rect 
                x="4" y="4" 
                width="40" height="40" 
                rx="12" 
                fill="none" 
                stroke="white" 
                stroke-width="1" 
                opacity="0.2"
            />
            
            <!-- Back bubble -->
            <path 
                d="M14 14C14 11.79 15.79 10 18 10H30C32.21 10 34 11.79 34 14V22C34 24.21 32.21 26 30 26H22L18 30V26H18C15.79 26 14 24.21 14 22V14Z"
                fill="white"
                opacity="0.2"
            />
            
            <!-- Front bubble -->
            <path 
                d="M18 20C18 17.79 19.79 16 22 16H34C36.21 16 38 17.79 38 20V28C38 30.21 36.21 32 34 32H26L22 36V32H22C19.79 32 18 30.21 18 28V20Z"
                fill="white"
                opacity="0.95"
                filter="url(#glow)"
                class="bubble"
            />
            
            <!-- Number 2 -->
            <text 
                x="28" y="28" 
                font-family="Inter, system-ui, sans-serif" 
                font-size="11" 
                font-weight="800" 
                text-anchor="middle"
                fill="#2563eb"
                class="logo-text"
            >
                2
            </text>
            
            <!-- Decorative dots -->
            <circle cx="10" cy="38" r="2" fill="white" opacity="0.35" class="dot-1"/>
            <circle cx="10" cy="44" r="1" fill="white" opacity="0.2" class="dot-2"/>
        </svg>
    `,
    styles: [`
        :host {
            display: inline-flex;
        }
        
        .logo {
            transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        }
        
        :host:hover .logo {
            transform: translateY(-2px) scale(1.03);
            filter: drop-shadow(0 12px 30px rgba(59, 130, 246, 0.5));
        }
        
        .bubble {
            transition: transform 0.3s ease;
        }
        
        :host:hover .bubble {
            transform: translateY(-1px);
        }
        
        .dot-1, .dot-2 {
            transition: all 0.3s ease;
        }
        
        :host:hover .dot-1 {
            opacity: 0.5;
            transform: translateX(1px);
        }
        
        :host:hover .dot-2 {
            opacity: 0.35;
            transform: translateX(2px);
        }
    `]
})
export class LogoGeometricComponent {
    @Input() size: number = 36;
}