// Libera.app's executable.
//
// Finder does not pass a double-clicked document in argv; it sends the process
// an Apple Event, and only an NSApplication with a delegate receives one. That
// process must be the bundle's own executable: a shell script that exec's
// Python does not work, because after the exec the process belongs to
// Python.app and the event is delivered to a bundle that no longer exists.
//
// So this catches the event, then hands the paths to the Python entry point as
// ordinary arguments -- and runs that entry point in this process, with the
// interpreter embedded, rather than exec'ing it. An exec was the second half
// of the same problem: from then on macOS took the running application for
// Python.app (lsappinfo: bundleID "org.python.python"), so a document dropped
// on the Dock icon was refused in Python's name, against Python.app's empty
// list of document types, before anything of ours saw it. Embedded, the
// process stays this bundle's, with this bundle's document types.
//
//   clang -framework Cocoa -I<python include> <libpython> \
//       -DLIBERA_PYTHON='"/path/to/python3"' launcher.m
//
// LIBERA_PYTHON is the interpreter the bundle runs as. Absolute, it is a
// virtualenv's python3 on the machine that built the bundle, whose pyvenv.cfg
// is how the embedded interpreter finds its packages. Relative, it is inside
// the bundle, under Contents, and the bundle carries everything
// (STANDALONE=1 build/macos/macos-app.sh).

// First, as Python asks: it sets feature macros the system headers read.
#include <Python.h>
#import <Cocoa/Cocoa.h>
#include <stdlib.h>
#include <string.h>

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
        NSString *python = @LIBERA_PYTHON;
        BOOL inside = ![python isAbsolutePath];
        if (inside)
            python = [[[[NSBundle mainBundle] bundlePath]
                stringByAppendingPathComponent:@"Contents"]
                stringByAppendingPathComponent:python];
        [args addObject:python];
        [args addObject:@"-m"];
        [args addObject:@"libera"];
        [args addObjectsFromArray:gDocuments];
        // AppKit also reads the command line: started from a terminal with a
        // file, it delivers that file as an open-documents event too, so it
        // was passed twice, and `-v --serve FILE` was refused with "unrecognized
        // arguments: FILE" (measured: LIBERA_LAUNCHER_LOG said docs=1 for a
        // launch with no Finder in it). An argument already caught is skipped.
        NSMutableSet<NSString *> *caught = [NSMutableSet set];
        for (NSString *d in gDocuments) [caught addObject:[d stringByStandardizingPath]];
        NSString *cwd = [[NSFileManager defaultManager] currentDirectoryPath];
        for (int i = 1; i < argc; i++) {
            NSString *a = [NSString stringWithUTF8String:argv[i]];
            // LaunchServices appends a process serial number on some launches.
            if ([a hasPrefix:@"-psn_"]) continue;
            NSString *full = [a isAbsolutePath] ? a : [cwd stringByAppendingPathComponent:a];
            if (![a hasPrefix:@"-"] && [caught containsObject:[full stringByStandardizingPath]])
                continue;
            [args addObject:a];
        }

        // The interpreter's own idea of where it is, set in its configuration
        // rather than in PYTHONEXECUTABLE, which every child would inherit.
        // From it comes everything else: the virtualenv beside it, and so
        // the libera package. A library that cannot be loaded never gets
        // here -- dyld stops the process first -- and the bundle has to be
        // rebuilt (build/macos/macos-app.sh).
        int count = (int)[args count];
        char **cargs = calloc(count + 1, sizeof(char *));
        for (int i = 0; i < count; i++) cargs[i] = strdup([args[i] UTF8String]);

        PyConfig config;
        PyConfig_InitPythonConfig(&config);
        // Nothing is written into a bundle, which signing seals: its
        // bytecode was compiled when it was built.
        if (inside) config.write_bytecode = 0;
        PyStatus status =
            PyConfig_SetBytesString(&config, &config.executable, [python UTF8String]);
        if (!PyStatus_Exception(status))
            status = PyConfig_SetBytesArgv(&config, count, cargs);
        if (!PyStatus_Exception(status)) status = Py_InitializeFromConfig(&config);
        PyConfig_Clear(&config);
        if (PyStatus_Exception(status)) Py_ExitStatusException(status);
        return Py_RunMain();
    }
}
