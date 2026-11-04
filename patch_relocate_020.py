#!/usr/bin/env python3
"""Relocate 0.1.20: Apple Maps-only CLLocationManager lifecycle diagnostics.

Apply AFTER 015, 016, 017, 018, 019 to a clean Tweak/Tweak.xm.
No coordinates or location objects are logged. No spoofing behavior changes.
"""
from pathlib import Path
import sys

p = Path(sys.argv[1] if len(sys.argv) > 1 else 'Tweak/Tweak.xm')
s = p.read_text(encoding='utf-8')
if 'RLC020TraceManager(' in s:
    raise SystemExit('RLC020 already applied')
if 'RLC019Probe(' not in s or 'RLC018Trace(' not in s:
    raise SystemExit('Apply 015 through 019 before 020')

anchor = '@implementation RLCManager'
if s.count(anchor) != 1:
    raise SystemExit('RLCManager implementation not unique')
helper = r'''// RLC020: Apple Maps-only manager identity and lifecycle diagnostics.
// ID numbers are session-local; no memory addresses or coordinates are logged.
static void RLC020TraceManager(NSString *event, CLLocationManager *manager, id incomingDelegate, id proxy) {
    if (![[NSProcessInfo processInfo].processName isEqualToString:@"Maps"]) return;
    if (!manager) return;
    static char managerIDKey;
    static NSUInteger nextManagerID = 0;
    static NSMutableDictionary *eventCounts = nil;
    @synchronized ([CLLocationManager class]) {
        NSNumber *managerID = objc_getAssociatedObject(manager, &managerIDKey);
        if (!managerID) {
            managerID = @(++nextManagerID);
            objc_setAssociatedObject(manager, &managerIDKey, managerID, OBJC_ASSOCIATION_RETAIN_NONATOMIC);
        }
        if (!eventCounts) eventCounts = [NSMutableDictionary new];
        NSUInteger n = [eventCounts[event] unsignedIntegerValue] + 1;
        eventCounts[event] = @(n);
        if (n > 16 && n % 100 != 0) return;
        // Inspect the caller-supplied Relocate proxy, not location data.
        id wrapped = [proxy respondsToSelector:@selector(delegate)] ? [proxy delegate] : nil;
        NSString *runtimeClass = NSStringFromClass(object_getClass(manager)) ?: @"unknown";
        RLCFileDebugLog([NSString stringWithFormat:
            @"RLC020 event=%@ count=%lu manager-id=%@ class=%@ incoming=%d proxy=%d wrapped=%d active=%d",
            event, (unsigned long)n, managerID, runtimeClass,
            incomingDelegate != nil, proxy != nil, wrapped != nil, enabled]);
    }
}

'''
s = '#import <objc/runtime.h>\n' + s
s = s.replace(anchor, helper + anchor, 1)
changes = [
    ('-(void)setDelegate:(id)delegate {\n    RLC018Trace(@"manager.setDelegate", enabled, noGPSMode, 1);',
     '-(void)setDelegate:(id)delegate {\n    RLC020TraceManager(@"setDelegate.enter", self, delegate, self.rlcDelegate);\n    RLC018Trace(@"manager.setDelegate", enabled, noGPSMode, 1);'),
    ('    RLC019Probe(@"setDelegate.proxyAssigned", self.rlcDelegate.delegate, self.rlcDelegate);',
     '    RLC019Probe(@"setDelegate.proxyAssigned", self.rlcDelegate.delegate, self.rlcDelegate);\n    RLC020TraceManager(@"setDelegate.assigned", self, delegate, self.rlcDelegate);'),
    ('-(id)delegate {\n    RLC019Probe(@"delegate.getter", self.rlcDelegate.delegate, self.rlcDelegate);',
     '-(id)delegate {\n    RLC020TraceManager(@"delegate.getter", self, nil, self.rlcDelegate);\n    RLC019Probe(@"delegate.getter", self.rlcDelegate.delegate, self.rlcDelegate);'),
    ('-(void)startUpdatingLocation {\n    RLC018Trace(@"manager.startUpdatingLocation", enabled, noGPSMode, 1);',
     '-(void)startUpdatingLocation {\n    RLC020TraceManager(@"startUpdating", self, nil, self.rlcDelegate);\n    RLC018Trace(@"manager.startUpdatingLocation", enabled, noGPSMode, 1);'),
    ('-(void)requestLocation {\n    RLC018Trace(@"manager.requestLocation", enabled, noGPSMode, 1);',
     '-(void)requestLocation {\n    RLC020TraceManager(@"requestLocation", self, nil, self.rlcDelegate);\n    RLC018Trace(@"manager.requestLocation", enabled, noGPSMode, 1);'),
    ('- (void)startUpdatingLocationWithPrompt {\n    [[RLCManager sharedInstance] addManager:self];',
     '- (void)startUpdatingLocationWithPrompt {\n    RLC020TraceManager(@"startUpdatingWithPrompt", self, nil, self.rlcDelegate);\n    [[RLCManager sharedInstance] addManager:self];'),
    ('-(void)stopUpdatingLocation {\n    [[RLCManager sharedInstance] removeManager:self];',
     '-(void)stopUpdatingLocation {\n    RLC020TraceManager(@"stopUpdating", self, nil, self.rlcDelegate);\n    [[RLCManager sharedInstance] removeManager:self];'),
]
for before, after in changes:
    n = s.count(before)
    if n != 1:
        raise SystemExit(f'Expected one anchor, found {n}: {before[:100]}')
    s = s.replace(before, after, 1)

# Trace newly created managers without modifying return values.
init_anchor = '%hook CLLocationManager\n\n%property (nonatomic, retain) RLCLocationManagerDelegate* rlcDelegate;'
if s.count(init_anchor) != 1:
    raise SystemExit('CLLocationManager hook anchor missing')
init_replacement = init_anchor + '''\n\n-(instancetype)init {\n    id result = %orig;\n    RLC020TraceManager(@"init", result, nil, nil);\n    return result;\n}'''
s = s.replace(init_anchor, init_replacement, 1)
p.write_text(s, encoding='utf-8')
print('RLC020 Apple Maps lifecycle diagnostics applied:', p)
