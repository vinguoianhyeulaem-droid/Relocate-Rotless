#!/usr/bin/env python3
"""Relocate 0.1.23: app-target / global selection extension on merged 0.1.22.

Usage from repository root, AFTER applying the 0.1.22 consolidated patch:
    python3 patch_relocate_023.py Tweak/Tweak.xm

Updates Tweak.xm and the existing Relocate injection filter in Tweak/Relocate.plist
(or Relocate.plist at repo root). Leaves the working Google/Apple Maps coordinate
hooks unchanged. Fails closed if expected source/filters are not recognized.
"""
from pathlib import Path
import re
import sys

source = Path(sys.argv[1] if len(sys.argv) > 1 else "Tweak/Tweak.xm")
if not source.is_file():
    sys.exit(f"Source missing: {source}")

text = source.read_text(encoding="utf-8")
marker = "// RLC023 target/global app policy"
if marker in text:
    print("RLC023 source already patched")
    source_modified = False
    updated = text
else:
    if "RLC017RefreshPrefs" not in text or "RLC022 Apple Maps experiment" not in text:
        sys.exit("Expected consolidated Relocate 0.1.22 source; apply merged patch first")
    old = '''        BOOL useOverride = master && (global || (perApp && mode == 1));
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
'''
    new = '''        // RLC023 target/global app policy: mode 0=inherit global, 1=targeted,
        // 2=explicitly excluded. Target-only never leaks to unselected apps.
        BOOL selected = perApp && mode == 1;
        BOOL excluded = perApp && mode == 2;
        BOOL useOverride = master && !excluded && (global || selected);
        NSDictionary *nextLocation = nil;
        if (selected) {
            nextLocation = diskPrefs[[NSString stringWithFormat:@"App_%@_Location", bundleID]];
            // An app selected for override can share the global pin when
            // no app-specific pin has been saved yet.
            NSDictionary *appCoord = [nextLocation isKindOfClass:[NSDictionary class]] ? nextLocation[@"Coordinate"] : nil;
            if (![appCoord isKindOfClass:[NSDictionary class]] ||
                ![appCoord[@"Latitude"] respondsToSelector:@selector(doubleValue)] ||
                ![appCoord[@"Longitude"] respondsToSelector:@selector(doubleValue)]) {
                nextLocation = diskPrefs[@"GlobalLocation"];
            }
        } else if (global) {
            nextLocation = diskPrefs[@"GlobalLocation"];
        }

        NSDictionary *coord = [nextLocation isKindOfClass:[NSDictionary class]] ? nextLocation[@"Coordinate"] : nil;
        NSNumber *lat = [coord isKindOfClass:[NSDictionary class]] ? coord[@"Latitude"] : nil;
        NSNumber *lon = [coord isKindOfClass:[NSDictionary class]] ? coord[@"Longitude"] : nil;
        BOOL valid = [lat respondsToSelector:@selector(doubleValue)] &&
                     [lon respondsToSelector:@selector(doubleValue)] &&
                     isfinite(lat.doubleValue) && isfinite(lon.doubleValue) &&
                     lat.doubleValue >= -90.0 && lat.doubleValue <= 90.0 &&
                     lon.doubleValue >= -180.0 && lon.doubleValue <= 180.0;
        enabled = useOverride && valid;
'''
    if text.count(old) != 1:
        sys.exit("RLC017 app policy not found uniquely. Refusing to modify source")
    updated = text.replace(old, new, 1)
    # Add math header for isfinite, without modifying hooks.
    header = "#import <math.h>\n"
    if header not in updated:
        updated = header + updated
    updated = updated.replace("// RLC017: Refresh effective prefs", marker + "\n// RLC017: Refresh effective prefs", 1)
    source_modified = True

# We intentionally preserve the original CoreLocation bundle trigger. This
# reaches app processes which load the framework, while constructor guards
# still exclude normal non-app processes. Explicit Maps entries ensure the
# two already tested apps stay in the injection filter.
filter_text = '''{ Filter = { Bundles = (
    "com.apple.corelocation",
    "com.apple.Maps",
    "com.google.Maps"
); }; }
'''
root = source.parent.parent if source.parent.name == "Tweak" else source.parent
candidates = [root / "Tweak" / "Relocate.plist", root / "Relocate.plist"]
existing = [p for p in candidates if p.is_file()]
if not existing:
    sys.exit("Could not locate Relocate.plist. Expected Tweak/Relocate.plist "
             "or Relocate.plist. No source changes written.")
if len(existing) > 1:
    sys.exit("Two Relocate.plist files found; cannot determine build input. "
             "No source changes written.")
filter_path = existing[0]
current_filter = filter_path.read_text(encoding="utf-8")
if not re.search(r"\bFilter\b", current_filter) or not re.search(r"\bBundles\b", current_filter):
    sys.exit("Existing injection plist has an unfamiliar format. "
             "No source changes written.")
if re.search(r"\b(Executables|Classes|Mode|CoreFoundationVersion)\b", current_filter):
    sys.exit("Existing injection plist contains additional filters. "
             "Please review it manually. No source changes written.")

if source_modified:
    source.write_text(updated, encoding="utf-8")
    print("RLC023 app selection policy applied:", source)
if current_filter != filter_text:
    filter_path.write_text(filter_text, encoding="utf-8")
    print("RLC023 injection filter broadened:", filter_path)
else:
    print("Injection filter already current:", filter_path)
print("Done. The tested CoreLocation hooks are unchanged.")
