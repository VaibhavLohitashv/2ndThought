import { Pipe, PipeTransform } from '@angular/core';

@Pipe({ name: 'keys', standalone: true })
export class KeysPipe implements PipeTransform {
    transform(value: Record<number, any>): number[] {
        if (!value) return [];
        return Object.keys(value).map(key => Number(key));
    }
}
