// Libera.app's executable.
//
// Finder does not pass a double-clicked document in argv; it sends the process
// an Apple Event, and only an NSApplication with a delegate receives one. That
// process must be the bundle's own executable: a shell script that exec's
// Python does not work, because after the exec the process belongs to
// Python.app and the event is delivered to a bundle that no longer exists.
//
// So this catches the event, then hands the paths to the Python entry point as
// ordinary arguments.
//
//   clang -framework Cocoa -DLIBERA_PYTHON='"/path/to/python3"' launcher.m

#import <Cocoa/Cocoa.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static NSMutableArray<NSString *> *gDocuments;
static BOOL gLaunched;

@interface LiberaLauncher : NSObject <NSApplicationDelegate>
@end

@implementation LiberaLauncher
- (void)application:(NSApplication *)app openFiles:(NSArray<NSString *> *)files {
    [gDocuments addObjectsFromArray:files];
    [app replyToOpenOrPrint:NSApplicationDelegateReplySuccess];
}
- (void)applicationDidFinishLaunching:(NSNotification *)note {
    // AppKit sends this after the open-document event, so it marks the exact
    // end of the window in which a document can still arrive.
    (void)note;
    gLaunched = YES;
}
@end

int main(int argc, const char *argv[]) {
    @autoreleasepool {
        gDocuments = [NSMutableArray array];

        NSApplication *app = [NSApplication sharedApplication];
        LiberaLauncher *delegate = [[LiberaLauncher alloc] init];
        [app setDelegate:delegate];
        // A launcher with no window of its own is still a foreground app: this
        // is what makes AppKit deliver the launch events at all.
        [app setActivationPolicy:NSApplicationActivationPolicyRegular];
        // Nothing is delivered until the application says it is ready.
        [app finishLaunching];

        // Pump the application's own event queue, not just the run loop:
        // Apple Events reach a delegate through -[NSApplication sendEvent:],
        // and -[NSRunLoop runUntilDate:] never calls it. This is what -run
        // does, minus the part where it never returns.
        //
        // The stop condition is the document, not applicationDidFinishLaunching:
        // -- that is posted synchronously from finishLaunching, before the
        // queue has had a chance to deliver anything. Once it has fired, a
        // short settle is enough: a plain launch with no document must not sit
        // here for the full timeout.
        NSDate *deadline = [NSDate dateWithTimeIntervalSinceNow:5.0];
        NSDate *settle = nil;
        while ([gDocuments count] == 0 && [deadline timeIntervalSinceNow] > 0) {
            NSEvent *event =
                [app nextEventMatchingMask:NSEventMaskAny
                                 untilDate:[NSDate dateWithTimeIntervalSinceNow:0.02]
                                    inMode:NSDefaultRunLoopMode
                                   dequeue:YES];
            if (event) [app sendEvent:event];
            if (gLaunched && settle == nil)
                settle = [NSDate dateWithTimeIntervalSinceNow:0.5];
            if (settle && [settle timeIntervalSinceNow] <= 0) break;
        }
        if (getenv("LIBERA_LAUNCHER_LOG")) {
            FILE *f = fopen(getenv("LIBERA_LAUNCHER_LOG"), "a");
            if (f) {
                fprintf(f, "launched=%d docs=%lu bundle=%s\n", (int)gLaunched,
                        (unsigned long)[gDocuments count],
                        [[[NSBundle mainBundle] bundlePath] UTF8String]);
                fclose(f);
            }
        }

        // python3 -m libera [documents...] [any argv we were given]
        //
        // No verb. The file decides which editor opens it -- see
        // src/libera/host/apps.py -- and with no documents this opens the
        // start window, which is what double-clicking the icon should do.
        NSMutableArray<NSString *> *args = [NSMutableArray array];
        [args addObject:@LIBERA_PYTHON];
        [args addObject:@"-m"];
        [args addObject:@"libera"];
        [args addObjectsFromArray:gDocuments];
        for (int i = 1; i < argc; i++) {
            NSString *a = [NSString stringWithUTF8String:argv[i]];
            // LaunchServices appends a process serial number on some launches.
            if (![a hasPrefix:@"-psn_"]) [args addObject:a];
        }

        char **cargs = calloc([args count] + 1, sizeof(char *));
        for (NSUInteger i = 0; i < [args count]; i++)
            cargs[i] = strdup([args[i] UTF8String]);

        execv(cargs[0], cargs);
        // Only reached if the interpreter is gone -- say so where a user can
        // see it, since a bundle's stderr goes to the system log.
        NSString *msg = [NSString stringWithFormat:
            @"Libera Suite could not start its Python interpreter:\n%@\n\n"
             "The application bundle points at the interpreter it was built "
             "with. Rebuild it with build/macos-app.sh.", @LIBERA_PYTHON];
        NSAlert *alert = [[NSAlert alloc] init];
        [alert setMessageText:@"Libera Suite could not start"];
        [alert setInformativeText:msg];
        [alert runModal];
        return 1;
    }
}
