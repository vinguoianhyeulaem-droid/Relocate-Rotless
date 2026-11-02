#!/usr/bin/env python3
"""Relocate 0.1.16: compare HBPreferences flags with on-disk plist and
use disk flags only when an actual plist is readable. Apply AFTER 0.1.15.
No hook/joystick changes. Idempotent."""
from pathlib import Path
import sys
p = Path(sys.argv[1] if len(sys.argv) > 1 else 'Tweak/Tweak.xm')
s = p.read_text()
if 'RLC016 effective flags' in s:
    raise SystemExit('RLC016 already applied')
if 'RLCFileDebugLog(' not in s:
    raise SystemExit('Run the 0.1.15 diagnostic patch before this patch')
needle = '        noGPSMode = globalNoGPS;'
if s.count(needle) != 1:
    raise SystemExit('Could not locate unique preference callback')
replacement = '''        // RLC016 effective flags: HBPreferences cached pointer versus persisted plist.
        // A read failure never overrides the original preference flags.
        BOOL effectiveGlobalEnabled = globalEnabled;
        BOOL effectiveAppEnabled = appEnabled;
        BOOL effectiveGlobalNoGPS = globalNoGPS;
        NSDictionary *diskPrefs = nil;
        NSString *source = @"HBPreferences";
        NSArray *possiblePaths = @[
            @"/var/mobile/Library/Preferences/me.nepeta.relocate.plist",
            @"/var/jb/var/mobile/Library/Preferences/me.nepeta.relocate.plist"
        ];
        for (NSString *candidate in possiblePaths) {
            NSDictionary *candidatePrefs = [NSDictionary dictionaryWithContentsOfFile:candidate];
            if ([candidatePrefs isKindOfClass:[NSDictionary class]] && candidatePrefs.count > 0) {
                diskPrefs = candidatePrefs;
                source = @"disk-plist";
                break;
            }
        }
        if (diskPrefs) {
            id v = diskPrefs[@"GlobalEnabled"];
            if ([v respondsToSelector:@selector(boolValue)]) effectiveGlobalEnabled = [v boolValue];
            v = diskPrefs[@"AppEnabled"];
            if ([v respondsToSelector:@selector(boolValue)]) effectiveAppEnabled = [v boolValue];
            v = diskPrefs[@"GlobalNoGPS"];
            if ([v respondsToSelector:@selector(boolValue)]) effectiveGlobalNoGPS = [v boolValue];
        }
        RLCFileDebugLog([NSString stringWithFormat:
            @"RLC016 source=%@ cached-global=%d effective-global=%d cached-app=%d effective-app=%d disk-readable=%d",
            source, globalEnabled, effectiveGlobalEnabled, appEnabled,
            effectiveAppEnabled, diskPrefs != nil]);
        noGPSMode = effectiveGlobalNoGPS;'''
s=s.replace(needle,replacement,1)
# Restrict replacements to the single preference callback section.
start=s.index('        // RLC016 effective flags:')
end=s.index('        if (managerInitialized) [[RLCManager sharedInstance] update];',start)
chunk=s[start:end]
chunk=chunk.replace('        if (globalEnabled) {','        if (effectiveGlobalEnabled) {',1)
chunk=chunk.replace('        if (appEnabled && currentAppEnabled > 0) {','        if (effectiveAppEnabled && currentAppEnabled > 0) {',1)
chunk=chunk.replace('        if (appEnabled && currentAppEnabled != 2) {','        if (effectiveAppEnabled && currentAppEnabled != 2) {',1)
# Disk location fallback if HBPreferences misses the stored coordinate dict.
chunk=chunk.replace('            locationDict = [preferences objectForKey:@"GlobalLocation"];',
'''            locationDict = [preferences objectForKey:@"GlobalLocation"];
            if (![locationDict isKindOfClass:[NSDictionary class]] && diskPrefs) {
                locationDict = diskPrefs[@"GlobalLocation"];
            }''',1)
chunk=chunk.replace('            locationDict = [preferences objectForKey:[NSString stringWithFormat:@"App_%@_Location", bundleIdentifier]];',
'''            NSString *appLocationKey = [NSString stringWithFormat:@"App_%@_Location", bundleIdentifier];
            locationDict = [preferences objectForKey:appLocationKey];
            if (![locationDict isKindOfClass:[NSDictionary class]] && diskPrefs) {
                locationDict = diskPrefs[appLocationKey];
            }''',1)
# Include resolved activation flag even on early return.
chunk=chunk.replace('        if (!enabled) return;',
'''        if (!enabled) {
            RLCFileDebugLog(@"RLC016 activation=0 (no active override)");
            return;
        }''',1)
chunk=chunk.replace('        NSDictionary *coordinateDict = locationDict[@"Coordinate"];',
'''        RLCFileDebugLog([NSString stringWithFormat:@"RLC016 activation=1 location-valid=%d",
            [locationDict isKindOfClass:[NSDictionary class]] &&
            [locationDict[@"Coordinate"] isKindOfClass:[NSDictionary class]]]);
        NSDictionary *coordinateDict = locationDict[@"Coordinate"];''',1)
s=s[:start]+chunk+s[end:]
p.write_text(s)
print(f'RLC016 patched {p}')
