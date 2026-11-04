#!/usr/bin/env python3
"""Relocate 0.1.21: Apple Maps-only CoreLocation read-path diagnostics.

Apply after 015..020 to the original Tweak/Tweak.xm, on a clean checkout.
Read-only tracing. No changes to location return values or Google Maps behavior.
Does not record coordinates, addresses or object pointer values.
"""
from pathlib import Path
import sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else 'Tweak/Tweak.xm')
s = p.read_text(encoding='utf-8')
if 'RLC021Trace(' in s:
    raise SystemExit('RLC021 already applied')
if 'RLC020TraceManager(' not in s or 'RLC017RefreshPrefs' not in s:
    raise SystemExit('Apply patches 015 through 020 first')

anchor = '@implementation RLCManager'
if s.count(anchor) != 1:
    raise SystemExit('Expected exactly one RLCManager implementation')

helper = r'''// RLC021: Passive traces for Apple Maps only.
// Coordinates and location object addresses are never logged.
static void RLC021Trace(NSString *event, NSString *detail) {
    if (![[NSProcessInfo processInfo].processName isEqualToString:@"Maps"]) return;
    static NSMutableDictionary *counts = nil;
    @synchronized ([RLCManager class]) {
        if (!counts) counts = [NSMutableDictionary new];
        NSUInteger n = [counts[event] unsignedIntegerValue] + 1;
        counts[event] = @(n);
        if (n > 12 && (n % 200) != 0) return;
        RLCFileDebugLog([NSString stringWithFormat:
            @"RLC021 event=%@ count=%lu %@",
            event, (unsigned long)n, detail ?: @""]);
    }
}

'''
s = s.replace(anchor, helper + anchor, 1)

# This is an existing hook. Just log its status when Apple Maps calls it.
needle = '-(void)startUpdatingLocation {\n    RLC020TraceManager(@"startUpdating", self, nil, self.rlcDelegate);'
replacement = '''-(void)startUpdatingLocation {
    if ([[NSProcessInfo processInfo].processName isEqualToString:@"Maps"]) {
        CLAuthorizationStatus status = [self authorizationStatus];
        BOOL precise = YES;
        if ([self respondsToSelector:@selector(accuracyAuthorization)]) {
            precise = ([self accuracyAuthorization] == CLAccuracyAuthorizationFullAccuracy);
        }
        RLC021Trace(@"startUpdating.status", [NSString stringWithFormat:
            @"auth=%ld precise=%d enabled=%d noGPS=%d",
            (long)status, precise, enabled, noGPSMode]);
    }
    RLC020TraceManager(@"startUpdating", self, nil, self.rlcDelegate);'''
if s.count(needle) != 1:
    raise SystemExit(f'Expected one startUpdating hook; found {s.count(needle)}')
s = s.replace(needle, replacement, 1)

# Log whether any CLLocation instances have their coordinates accessed inside
# Apple Maps, independently of Relocate's delegate-proxy callbacks.
# Return untouched data from %orig. Do not alter GPS location values.
needle = '%hook CLLocationManager\n'
if s.count(needle) != 1:
    raise SystemExit(f'Expected one CLLocationManager hook; found {s.count(needle)}')
location_hook = '''%hook CLLocation

-(CLLocationCoordinate2D)coordinate {
    CLLocationCoordinate2D result = %orig;
    RLC021Trace(@"CLLocation.coordinate", @"read=1");
    return result;
}

%end

'''
s = s.replace(needle, location_hook + needle, 1)
p.write_text(s, encoding='utf-8')
print('RLC021 passive Apple Maps location read-path diagnostics applied:', p)
