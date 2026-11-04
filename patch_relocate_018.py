#!/usr/bin/env python3
"""Relocate 0.1.18: Apple Maps-only, read-only CoreLocation tracing.
Run after 015, 016, 017 on a clean source checkout. No GPS behavior changes.
"""
from pathlib import Path
import sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else 'Tweak/Tweak.xm')
s = p.read_text(encoding='utf-8')
if 'RLC018Trace(' in s:
    raise SystemExit('RLC018 already applied')
if 'RLC017RefreshPrefs' not in s or 'RLCFileDebugLog(' not in s:
    raise SystemExit('Apply 015, 016, 017 before 018')

helper = r'''// RLC018 Apple Maps diagnostic. No coordinates logged; no behavior changed.
// Limit logs to first 8 calls per event, then every 100th call.
static void RLC018Trace(NSString *event, BOOL active, BOOL noGPS, NSInteger quantity) {
    if (![[NSProcessInfo processInfo].processName isEqualToString:@"Maps"]) return;
    static NSMutableDictionary *counts = nil;
    @synchronized ([RLCManager class]) {
        if (!counts) counts = [NSMutableDictionary new];
        NSUInteger n = [counts[event] unsignedIntegerValue] + 1;
        counts[event] = @(n);
        if (n <= 8 || n % 100 == 0) {
            RLCFileDebugLog([NSString stringWithFormat:
                @"RLC018 event=%@ count=%lu enabled=%d noGPS=%d items=%ld",
                event, (unsigned long)n, active, noGPS, (long)quantity]);
        }
    }
}

'''
anchor = '@implementation RLCManager'
if s.count(anchor) != 1:
    raise SystemExit('Cannot find unique RLCManager implementation')
s=s.replace(anchor,helper+anchor,1)

# All anchors are deliberately specific and checked before writing.
changes = [
    ('- (void)locationManager:(CLLocationManager *)manager didUpdateLocations:(NSArray<CLLocation *> *)locations {\n    RLC017RefreshPrefs();',
     '- (void)locationManager:(CLLocationManager *)manager didUpdateLocations:(NSArray<CLLocation *> *)locations {\n    RLC017RefreshPrefs();\n    RLC018Trace(@"delegate.didUpdateLocations", enabled, noGPSMode, locations.count);'),
    ('- (void)locationManager:(CLLocationManager *)manager didUpdateToLocation:(CLLocation *)newLocation fromLocation:(CLLocation *)oldLocation {\n    RLC017RefreshPrefs();',
     '- (void)locationManager:(CLLocationManager *)manager didUpdateToLocation:(CLLocation *)newLocation fromLocation:(CLLocation *)oldLocation {\n    RLC017RefreshPrefs();\n    RLC018Trace(@"delegate.didUpdateToLocation", enabled, noGPSMode, 1);'),
    ('-(CLLocation *)location {\n    RLC017RefreshPrefs();',
     '-(CLLocation *)location {\n    RLC017RefreshPrefs();\n    RLC018Trace(@"manager.location", enabled, noGPSMode, 1);'),
    ('-(void)setDelegate:(id)delegate {',
     '-(void)setDelegate:(id)delegate {\n    RLC018Trace(@"manager.setDelegate", enabled, noGPSMode, 1);'),
    ('-(void)startUpdatingLocation {',
     '-(void)startUpdatingLocation {\n    RLC018Trace(@"manager.startUpdatingLocation", enabled, noGPSMode, 1);'),
    ('-(void)requestLocation {',
     '-(void)requestLocation {\n    RLC018Trace(@"manager.requestLocation", enabled, noGPSMode, 1);'),
]
for before, after in changes:
    count=s.count(before)
    if count != 1:
        raise SystemExit(f'Expected exactly one anchor (found {count}): {before[:80]}')
    s=s.replace(before,after,1)

p.write_text(s,encoding='utf-8')
print('RLC018 Apple Maps diagnostics applied:',p)
