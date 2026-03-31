import OCL from './openchemlib-full.js';

if (typeof window !== 'undefined' && !window.OCL) {
  window.OCL = OCL;
}
