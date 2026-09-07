import { describe, expect, it } from 'vitest';
import { detectPlatformFromUrl } from './api';

describe('detectPlatformFromUrl', () => {
  it('detects each supported platform from profile URLs', () => {
    expect(detectPlatformFromUrl('https://www.instagram.com/example/')).toBe('instagram');
    expect(detectPlatformFromUrl('https://www.linkedin.com/in/example')).toBe('linkedin');
    expect(detectPlatformFromUrl('https://www.facebook.com/example')).toBe('facebook');
    expect(detectPlatformFromUrl('https://www.reddit.com/user/example/')).toBe('reddit');
  });

  it('returns null for usernames and unknown hosts', () => {
    expect(detectPlatformFromUrl('example')).toBeNull();
    expect(detectPlatformFromUrl('https://unknown.example.com/x')).toBeNull();
  });
});
