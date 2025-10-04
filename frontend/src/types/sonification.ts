export type SonificationMode = 'transit-ping' | 'flux-pitch' | 'odd-even';

export type SonificationData = {
  phase: number[];
  flux: number[];
  inTransitMask: boolean[];
  oddEvenMask: ('odd' | 'even')[];
};

export type SonificationSettings = {
  mode: SonificationMode;
  quantize: boolean;
  speed: 1 | 2;
  volume: number;
};
