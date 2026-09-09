import { ChangeDetectionStrategy, Component } from '@angular/core';

@Component({
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [],
  selector: 'tmt-root',
  styleUrl: './app.scss',
  templateUrl: './app.html',
})
export class App {}
