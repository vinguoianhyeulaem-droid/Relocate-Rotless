#!/usr/bin/env python3
"""Add non-invasive per-process file diagnostics to Relocate Tweak.xm.
Run from repository root: python3 patch_relocate_015.py Tweak/Tweak.xm
"""
from pathlib import Path
import sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else 'Tweak/Tweak.xm')
s = p.read_text()
if 'RLCFileDebugLog(' in s:
    raise SystemExit('Already patched; not changing file.')
needle = '%ctor {'
if s.count(needle) != 1:
    raise SystemExit(f'Expected one %ctor, found {s.count(needle)}')
helper = r'''// RLC015 diagnostic only. Writes to each process's sandbox-writable Caches directory.
// No coordinates, tokens, or private user data are recorded.
static void RLCFileDebugLog(NSString *message) {
    @try {
        NSArray *dirs = NSSearchPathForDirectoriesInDomains(NSCachesDirectory, NSUserDomainMask, YES);
        if (dirs.count == 0) return;
        NSString *dir = dirs.firstObject;
        [[NSFileManager defaultManager] createDirectoryAtPath:dir
                                  withIntermediateDirectories:YES attributes:nil error:nil];
        NSString *file = [dir stringByAppendingPathComponent:@"RelocateDebug.log"];
        NSString *line = [NSString stringWithFormat:@"%@ [%@ pid=%d] %@\n",
                          [NSDate date], [NSProcessInfo processInfo].processName,
                          getpid(), message];
        NSData *data = [line dataUsingEncoding:NSUTF8StringEncoding];
        int fd = open(file.fileSystemRepresentation, O_WRONLY | O_CREAT | O_APPEND, 0600);
        if (fd >= 0) {
            write(fd, data.bytes, data.length);
            close(fd);
        } else {
            NSLog(@"[RLCDBG] File log unavailable (%d) at %@: %@", errno, file, message);
        }
    } @catch (NSException *e) {
        NSLog(@"[RLCDBG] File logger failed: %@", e.name);
    }
}

'''
s = '#import <fcntl.h>\n#import <unistd.h>\n#import <errno.h>\n' + s
s = s.replace(needle, helper + needle + '\n    RLCFileDebugLog(@"constructor entered");', 1)
s = s.replace('    dpkgInvalid = ![[NSFileManager defaultManager] fileExistsAtPath:PLIST_PATH];',
              '    dpkgInvalid = ![[NSFileManager defaultManager] fileExistsAtPath:PLIST_PATH];\n    RLCFileDebugLog([NSString stringWithFormat:@"package-file-exists=%d", !dpkgInvalid]);', 1)
s = s.replace('    if (dpkgInvalid) {\n        %init(RelocateIntegrityFail);',
              '    if (dpkgInvalid) {\n        RLCFileDebugLog(@"constructor blocked: package validation");\n        %init(RelocateIntegrityFail);', 1)
s = s.replace('        if (!shouldLoad) return;',
              '        if (!shouldLoad) {\n            RLCFileDebugLog(@"constructor blocked: shouldLoad=0");\n            return;\n        }', 1)
s = s.replace('    preferences = [[HBPreferences alloc] initWithIdentifier:@"me.nepeta.relocate"];',
              '    RLCFileDebugLog(@"constructor allowed: creating HBPreferences");\n    preferences = [[HBPreferences alloc] initWithIdentifier:@"me.nepeta.relocate"];', 1)
s = s.replace('    [preferences registerPreferenceChangeBlock:^() {',
              '    [preferences registerPreferenceChangeBlock:^() {\n        RLCFileDebugLog([NSString stringWithFormat:@"prefs callback: enabled=%d global=%d app=%d", rlcEnabled, globalEnabled, appEnabled]);', 1)
s = s.replace('        if (managerInitialized) [[RLCManager sharedInstance] update];',
              '        RLCFileDebugLog([NSString stringWithFormat:@"prefs applied: active=%d location-dict-present=%d", enabled, [locationDict isKindOfClass:[NSDictionary class]]]);\n        if (managerInitialized) [[RLCManager sharedInstance] update];', 1)
s = s.replace('    %init(Relocate);',
              '    RLCFileDebugLog(@"before %init(Relocate)");\n    %init(Relocate);\n    RLCFileDebugLog(@"after %init(Relocate)");', 1)
p.write_text(s)
print(f'Patched {p}; logging to process Caches/RelocateDebug.log')
