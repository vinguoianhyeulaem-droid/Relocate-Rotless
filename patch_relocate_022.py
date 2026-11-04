#!/usr/bin/env python3
"""Relocate 0.1.22 experimental Apple Maps CLLocation.coordinate override.

Run AFTER patches 015..021 against original Tweak/Tweak.xm.
Changes only the existing CLLocation coordinate hook added by 021.
Google Maps is unaffected. Does not alter CLLocation storage, timestamps or GPS manager.
"""
from pathlib import Path
import sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else 'Tweak/Tweak.xm')
s = p.read_text(encoding='utf-8')
if 'RLC022 Apple Maps experiment' in s:
    raise SystemExit('RLC022 already applied')
if 'RLC021Trace(' not in s or 'RLC017RefreshPrefs' not in s:
    raise SystemExit('Apply patches 015 through 021 first')
old = '''-(CLLocationCoordinate2D)coordinate {
    CLLocationCoordinate2D result = %orig;
    RLC021Trace(@"CLLocation.coordinate", @"read=1");
    return result;
}'''
if s.count(old) != 1:
    raise SystemExit(f'Expected exactly one RLC021 CLLocation coordinate hook, found {s.count(old)}')
new = '''// RLC022 Apple Maps experiment: override only recent, plausible GPS fixes.
// This getter is also used for map features, so never override old/unknown fixes.
-(CLLocationCoordinate2D)coordinate {
    CLLocationCoordinate2D result = %orig;
    if (![[NSProcessInfo processInfo].processName isEqualToString:@"Maps"]) return result;

    RLC017RefreshPrefs();
    if (!enabled || noGPSMode || !CLLocationCoordinate2DIsValid(coordinate)) {
        RLC021Trace(@"CLLocation.coordinate", @"RLC022 pass=disabled");
        return result;
    }

    // No interception of old points of interest, route geometry, or invalid data.
    // A recently constructed map point with realistic GPS metadata can still
    // match this heuristic: treat this build as experimental, not production.
    NSDate *stamp = self.timestamp;
    CLLocationAccuracy accuracy = self.horizontalAccuracy;
    NSTimeInterval age = stamp ? [[NSDate date] timeIntervalSinceDate:stamp] : DBL_MAX;
    BOOL fresh = (age >= -3.0 && age <= 15.0);
    BOOL accurate = (accuracy >= 0.0 && accuracy <= 100.0);
    BOOL nonzero = CLLocationCoordinate2DIsValid(result) &&
                   !(result.latitude == 0.0 && result.longitude == 0.0);
    if (!fresh || !accurate || !nonzero) {
        RLC021Trace(@"CLLocation.coordinate", @"RLC022 pass=not-current-fix");
        return result;
    }

    RLC021Trace(@"CLLocation.coordinate", @"RLC022 action=override");
    return coordinate;
}'''
s = s.replace(old, new, 1)
# DBL_MAX defined by float.h. Imported at top to avoid relying on implicit SDK includes.
if '#import <float.h>\n' not in s:
    s = '#import <float.h>\n' + s
p.write_text(s, encoding='utf-8')
print('RLC022 Apple Maps-only experimental location coordinate hook applied:', p)
