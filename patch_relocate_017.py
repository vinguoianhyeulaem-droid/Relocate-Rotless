#!/usr/bin/env python3
"""Relocate 0.1.17: live, per-process preference refresh for CoreLocation callbacks.
Run after patches 015 and 016. Keep original hooks, UI, and coordinate logic.
"""
from pathlib import Path
import sys
p=Path(sys.argv[1] if len(sys.argv)>1 else 'Tweak/Tweak.xm')
s=p.read_text()
if 'RLC017RefreshPrefs' in s:
    raise SystemExit('RLC017 already applied')
if 'RLC016 effective flags' not in s or 'RLCFileDebugLog(' not in s:
    raise SystemExit('Apply patches 015 and 016 before 017')
marker='@implementation RLCManager'
if s.count(marker)!=1:
    raise SystemExit('RLCManager implementation marker missing/not unique')
helper=r'''// RLC015 defines this logger before %ctor, below RLCManager.
// Forward declaration is required because the RLC017 helper is inserted earlier.
static void RLCFileDebugLog(NSString *message);

// RLC017: Refresh effective prefs at actual CoreLocation entry points.
// This addresses cached HBPreferences values when Settings toggles while apps stay alive.
// No file writes; if disk preferences are inaccessible, preserve the previous state.
static void RLC017RefreshPrefs(void) {
    static NSTimeInterval lastCheck = 0;
    @synchronized ([RLCManager class]) {
        NSTimeInterval now = [NSProcessInfo processInfo].systemUptime;
        if (now - lastCheck < 0.35) return;
        lastCheck = now;

        NSDictionary *diskPrefs = nil;
        for (NSString *path in @[
            @"/var/mobile/Library/Preferences/me.nepeta.relocate.plist",
            @"/var/jb/var/mobile/Library/Preferences/me.nepeta.relocate.plist"
        ]) {
            NSDictionary *candidate = [NSDictionary dictionaryWithContentsOfFile:path];
            if ([candidate isKindOfClass:[NSDictionary class]] && candidate.count > 0) {
                diskPrefs = candidate;
                break;
            }
        }
        if (!diskPrefs) return;
        BOOL oldEnabled = enabled;
        BOOL oldNoGPS = noGPSMode;
        BOOL master = [diskPrefs[@"Enabled"] respondsToSelector:@selector(boolValue)]
            ? [diskPrefs[@"Enabled"] boolValue] : rlcEnabled;
        BOOL global = [diskPrefs[@"GlobalEnabled"] respondsToSelector:@selector(boolValue)]
            ? [diskPrefs[@"GlobalEnabled"] boolValue] : globalEnabled;
        BOOL perApp = [diskPrefs[@"AppEnabled"] respondsToSelector:@selector(boolValue)]
            ? [diskPrefs[@"AppEnabled"] boolValue] : appEnabled;
        BOOL noGPS = [diskPrefs[@"GlobalNoGPS"] respondsToSelector:@selector(boolValue)]
            ? [diskPrefs[@"GlobalNoGPS"] boolValue] : globalNoGPS;
        NSString *bundleID = [NSBundle mainBundle].bundleIdentifier ?: @"";
        NSNumber *appMode = diskPrefs[[NSString stringWithFormat:@"App_%@_Enabled", bundleID]];
        NSInteger mode = [appMode respondsToSelector:@selector(integerValue)] ? appMode.integerValue : 0;

        BOOL useOverride = master && (global || (perApp && mode == 1));
        if (perApp && mode == 2) useOverride = NO;
        NSDictionary *nextLocation = nil;
        if (perApp && mode == 1)
            nextLocation = diskPrefs[[NSString stringWithFormat:@"App_%@_Location", bundleID]];
        else if (global)
            nextLocation = diskPrefs[@"GlobalLocation"];

        NSDictionary *coord = [nextLocation isKindOfClass:[NSDictionary class]] ? nextLocation[@"Coordinate"] : nil;
        NSNumber *lat = [coord isKindOfClass:[NSDictionary class]] ? coord[@"Latitude"] : nil;
        NSNumber *lon = [coord isKindOfClass:[NSDictionary class]] ? coord[@"Longitude"] : nil;
        BOOL valid = [lat respondsToSelector:@selector(doubleValue)] && [lon respondsToSelector:@selector(doubleValue)];
        // Missing coordinates must not activate an override at (0,0).
        enabled = useOverride && valid;
        noGPSMode = enabled && noGPS;
        if (valid && enabled) {
            locationDict = nextLocation;
            coordinate = CLLocationCoordinate2DMake(lat.doubleValue, lon.doubleValue);
        }
        if (oldEnabled != enabled || oldNoGPS != noGPSMode) {
            RLCFileDebugLog([NSString stringWithFormat:
                @"RLC017 live master=%d global=%d app=%d mode=%ld valid=%d enabled=%d",
                master, global, perApp, (long)mode, valid, enabled]);
        }
    }
}

'''
s=s.replace(marker,helper+marker,1)
# Refresh before the fork between real / fabricated coordinates for modern + legacy delegates
needles=[
    '- (void)locationManager:(CLLocationManager *)manager didUpdateLocations:(NSArray<CLLocation *> *)locations {',
    '- (void)locationManager:(CLLocationManager *)manager didUpdateToLocation:(CLLocation *)newLocation fromLocation:(CLLocation *)oldLocation {',
    '-(CLLocation *)location {',
]
for n in needles:
    if s.count(n)!=1:
        raise SystemExit(f'Expected unique hook: {n}, found {s.count(n)}')
    s=s.replace(n,n+'\n    RLC017RefreshPrefs();',1)
# NoGPS timer: get latest master status before emitting another fabricated location.
n='-(void)update {\n    if (!enabled || !noGPSMode) return;'
if s.count(n)!=1: raise SystemExit('RLCManager update() anchor missing')
s=s.replace(n,'-(void)update {\n    RLC017RefreshPrefs();\n    if (!enabled || !noGPSMode) return;',1)
p.write_text(s)
print('RLC017 applied to',p)
