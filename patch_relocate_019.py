#!/usr/bin/env python3
"""Relocate 0.1.19: Apple Maps-only delegate/callback diagnostics.

Apply after 015, 016, 017, 018 on a clean checkout. No GPS behavior changes.
Does not record coordinates, location objects, or names of delegate classes.
"""
from pathlib import Path
import sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else 'Tweak/Tweak.xm')
s = p.read_text(encoding='utf-8')
if 'RLC019Probe(' in s:
    raise SystemExit('RLC019 already applied')
if 'RLC018Trace(' not in s or 'RLC017RefreshPrefs' not in s:
    raise SystemExit('Apply patches 015, 016, 017, 018 before 019')

# Trace function is defined after RLC018Trace and before RLCManager; it only
# examines delegate availability and selector support, never alters the delegates.
anchor = '@implementation RLCManager'
helper = r'''// RLC019 Apple Maps only: delegate-chain diagnostics; no GPS mutation.
static void RLC019Probe(NSString *event, id originalDelegate, id proxyDelegate) {
    if (![[NSProcessInfo processInfo].processName isEqualToString:@"Maps"]) return;
    static NSMutableDictionary *counts = nil;
    @synchronized ([RLCManager class]) {
        if (!counts) counts = [NSMutableDictionary new];
        NSUInteger count = [counts[event] unsignedIntegerValue] + 1;
        counts[event] = @(count);
        if (count > 8 && count % 100 != 0) return;
        BOOL originalModern = [originalDelegate respondsToSelector:@selector(locationManager:didUpdateLocations:)];
        BOOL originalLegacy = [originalDelegate respondsToSelector:@selector(locationManager:didUpdateToLocation:fromLocation:)];
        BOOL proxyModern = [proxyDelegate respondsToSelector:@selector(locationManager:didUpdateLocations:)];
        RLCFileDebugLog([NSString stringWithFormat:
            @"RLC019 event=%@ count=%lu original=%d proxy=%d original-modern=%d original-legacy=%d proxy-modern=%d enabled=%d noGPS=%d",
            event, (unsigned long)count, originalDelegate != nil, proxyDelegate != nil,
            originalModern, originalLegacy, proxyModern, enabled, noGPSMode]);
    }
}

'''
if s.count(anchor) != 1:
    raise SystemExit('Cannot find unique RLCManager implementation')
s = s.replace(anchor, helper + anchor, 1)

changes = [
    # The pre-018 hook wraps setDelegate: by assigning a proxy. Log before
    # the original implementation is called, without changing its arguments.
    ('-(void)setDelegate:(id)delegate {\n    RLC018Trace(@"manager.setDelegate", enabled, noGPSMode, 1);',
     '-(void)setDelegate:(id)delegate {\n    RLC018Trace(@"manager.setDelegate", enabled, noGPSMode, 1);\n    RLC019Probe(@"setDelegate.input", delegate, self.rlcDelegate);'),
    ('    self.rlcDelegate.delegate = delegate;\n\n    %orig(self.rlcDelegate);',
     '    self.rlcDelegate.delegate = delegate;\n    RLC019Probe(@"setDelegate.proxyAssigned", self.rlcDelegate.delegate, self.rlcDelegate);\n\n    %orig(self.rlcDelegate);'),
    ('-(id)delegate {\n    return self.rlcDelegate.delegate;\n}',
     '-(id)delegate {\n    RLC019Probe(@"delegate.getter", self.rlcDelegate.delegate, self.rlcDelegate);\n    return self.rlcDelegate.delegate;\n}'),
    # Apple Maps calls startUpdatingLocation without any observed setDelegate.
    # Log whether Relocate's proxy is installed at this point.
    ('-(void)startUpdatingLocation {\n    RLC018Trace(@"manager.startUpdatingLocation", enabled, noGPSMode, 1);',
     '-(void)startUpdatingLocation {\n    RLC018Trace(@"manager.startUpdatingLocation", enabled, noGPSMode, 1);\n    RLC019Probe(@"startUpdating.delegateState", self.rlcDelegate.delegate, self.rlcDelegate);'),
    ('-(void)requestLocation {\n    RLC018Trace(@"manager.requestLocation", enabled, noGPSMode, 1);',
     '-(void)requestLocation {\n    RLC018Trace(@"manager.requestLocation", enabled, noGPSMode, 1);\n    RLC019Probe(@"requestLocation.delegateState", self.rlcDelegate.delegate, self.rlcDelegate);'),
    # Existing proxy's didUpdate logging is from 018. Add other callbacks
    # to distinguish 'no location updates' from an authorization/error path.
    ('- (void)locationManager:(CLLocationManager *)manager didFailWithError:(NSError *)error {',
     '- (void)locationManager:(CLLocationManager *)manager didFailWithError:(NSError *)error {\n    RLC019Probe(@"delegate.didFailWithError", self.delegate, self);\n    if ([[NSProcessInfo processInfo].processName isEqualToString:@"Maps"]) {\n        RLCFileDebugLog([NSString stringWithFormat:@"RLC019 location-error-code=%ld", (long)error.code]);\n    }'),
    ('- (void)locationManager:(CLLocationManager *)manager didChangeAuthorizationStatus:(CLAuthorizationStatus)status {',
     '- (void)locationManager:(CLLocationManager *)manager didChangeAuthorizationStatus:(CLAuthorizationStatus)status {\n    RLC019Probe(@"delegate.didChangeAuthorization", self.delegate, self);'),
    ('- (void)locationManagerDidPauseLocationUpdates:(CLLocationManager *)manager {',
     '- (void)locationManagerDidPauseLocationUpdates:(CLLocationManager *)manager {\n    RLC019Probe(@"delegate.didPause", self.delegate, self);'),
    ('- (void)locationManagerDidResumeLocationUpdates:(CLLocationManager *)manager {',
     '- (void)locationManagerDidResumeLocationUpdates:(CLLocationManager *)manager {\n    RLC019Probe(@"delegate.didResume", self.delegate, self);'),
]
for before, after in changes:
    count = s.count(before)
    if count != 1:
        raise SystemExit(f'Expected exactly one anchor (found {count}): {before[:100]}')
    s = s.replace(before, after, 1)

p.write_text(s, encoding='utf-8')
print('RLC019 Apple Maps delegate diagnostics applied:', p)
