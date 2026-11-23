// lb, on one page. typst compile build/lb-cheatsheet.typ docs/src/pdf/lb-cheatsheet.pdf
// and commit the PDF with it: the developer docs link to it there.
//
// Every command in a `cmd` is a real command line, which
// build/tests/a_unit/test_lb_plan.py parses with lb's own parser: a rename
// that misses this page fails a test. Alternatives go in the description.

#set document(title: "lb cheat sheet", author: "Libera Suite")
#set page(
  paper: "a4",
  flipped: true,
  margin: (x: 0.9cm, top: 1.5cm, bottom: 0.8cm),
  columns: 3,
  header: context [
    #set text(size: 7pt, fill: luma(90))
    #text(size: 13pt, weight: "bold", fill: black)[`lb`]
    #h(0.4em) Libera Suite's build, packaging and release tool
    #h(1fr) `uv run lb` outside the virtualenv #h(0.6em)·#h(0.6em) builders: `python3 -m libera_build`
    #v(-0.3em)
    #line(length: 100%, stroke: 0.5pt + luma(150))
  ],
)
#set columns(gutter: 0.5cm)
#set text(font: ("Helvetica Neue", "Inter", "DejaVu Sans", "Libertinus Serif"), size: 7.2pt)
#show raw: set text(font: ("Menlo", "DejaVu Sans Mono"), size: 6.8pt)
#set par(leading: 0.42em, spacing: 0.5em)

#let accent = rgb("#1f5f8b")
#show heading.where(level: 1): it => block(above: 0.85em, below: 0.35em)[
  #set text(size: 8.6pt, weight: "bold", fill: accent)
  #it.body
  #v(-0.55em)
  #line(length: 100%, stroke: 0.4pt + accent)
]

// One command line and what it does, the second under the first. The command
// is kept as a string so the test can read it back.
#let cmd(line, what) = block(spacing: 0.55em, breakable: false)[
  #text(weight: "bold", raw(line))
  #block(above: 0.18em, inset: (left: 0.9em), text(fill: luma(55), what))
]
#let commands(..rows) = block(rows.pos().join())
#let note(body) = block(
  breakable: false,
  fill: luma(243),
  inset: 4pt,
  radius: 2pt,
  width: 100%,
  text(size: 6.8pt, body),
)

= Help
#commands(
  cmd("lb", [every command, and what is usually run]),
  cmd("lb help release check", [a group's commands, or one command's options and examples; `--help` works at every level]),
)
Each command prints the script it runs before running it; the scripts stay usable on their own. Every environment variable a script reads is also an option, and the option's help names it.

= Every day
#commands(
  cmd("lb payload check", [does the patch queue still apply to the pinned SHAs? (\~20 s)]),
  cmd("lb payload status", [which payload this checkout runs, and where from]),
  cmd("lb payload test", [the converter: fonts, docx → odt → docx, docx → pdf]),
  cmd("lb linux test", [the suite on Linux, in the test container]),
  cmd("lb linux test -k bridge", [anything after it goes to pytest]),
  cmd("lb linux test --gui", [the gui tier, a real GTK window under Xvfb]),
  cmd("lb linux lint", [the type checkers with the Linux branches live (`make lint-linux`)]),
)
#note[`make verify`: lint, the whole suite, docs links, `lb payload check`, `lb payload test`. `make test`, `make lint`, `make test-gui`: as in any Python project. `make payload` is `lb payload build`; `make ship VERSION=0.8.0` is `lb release check`, then `lb release publish 0.8.0`.]

= The payload
#commands(
  cmd("lb payload build", [every stage, then the test: hours, V8 about one]),
  cmd("lb payload build configure", [one stage: `fetch`, `configure`, `core`, `assemble`, `dist`; several run in that order]),
  cmd("lb payload build fetch --repo core", [one repository, at its pin, the queue applied; `--mirror DIR` for local clones]),
  cmd("lb payload build core --v8-jobs 4 --core-jobs 8", [x2t and the native libraries, the long one]),
  cmd("lb payload build dist --fonts full", [the tarballs and their manifest; `core` is the set that ships]),
  cmd("lb components build", [this machine's `libera-core` wheel, from its sdist, and `libera-web`'s; `--out DIR`]),
)
#note[`--build-root DIR` (`BUILD_ROOT`): `~/euro-office-build` on Linux, the external case-sensitive volume on macOS. `uv sync` builds the two components itself, from the pins.]

= Toolchain
#commands(
  cmd("lb toolchain check", [what is missing, in a second rather than an hour into a build]),
  cmd("lb toolchain list", [the packages this system needs, installing nothing]),
  cmd("lb toolchain install --dry-run", [what `install` would do; without `--dry-run`, it does it]),
)

#colbreak()

= Applications
#commands(
  cmd("lb app build macos", [the `.app`; `--standalone` puts Python, `libera` and the payload inside]),
  cmd("lb app build flatpak --arch arm64", [also `macos-launcher`, `flatpak-wheels`, `windows`]),
  cmd("lb app check flatpak", [the built Flatpak installed, `--diagnose` run in the sandbox]),
  cmd("lb app test flatpak", [the Flatpak converting a document under the GNOME runtime]),
  cmd("lb app test windows", [the gui tier, in a Windows window]),
  cmd("lb linux screenshot --dialog", [a GTK window under Xvfb, screenshotted; `--lang fr_FR.UTF-8`]),
)
#note[The `linux` commands install the component wheels of their architecture (`--wheels DIR`), or mount a payload as is (`--payload DIR`). `--arch amd64|arm64` defaults to this machine's.]

= Containers
#commands(
  cmd("lb container image payload", [build or rebuild an image: `payload`, `flatpak` or `linux`]),
  cmd("lb container versions payload", [what that image is pinned to]),
  cmd("lb container shell linux", [a shell in one]),
  cmd("lb container run payload", [the whole Linux payload build in its container]),
  cmd("lb container run payload dist.sh --fonts core", [or one `build/` script in it]),
  cmd("lb container export payload", [the artifacts, copied out; where to on stdout]),
  cmd("lb container clean flatpak", [the Flatpak builder's runtime volume, dropped (asks)]),
)
#note[`ENGINE=podman` or `docker`. A docker context that is a daemon over ssh cannot mount this tree, and `lb` says so.]

= On a builder
#commands(
  cmd("lb on linux-x86_64 app test flatpak", [any `lb` command, in that builder's checkout; output streams back]),
  cmd("lb on windows-x86_64 --update toolchain check", [this commit sent there first]),
)
#note[Builders: `build/builders.toml`. Platforms: `macos-arm64`, `linux-x86_64`, `linux-arm64`, `windows-x86_64`. Nothing interactive works through `lb on`.]

#colbreak()

= A release
#commands(
  cmd("lb release check --dry-run", [the plan, running nothing]),
  cmd("lb release check", [build and install everything as users will, as a candidate `0.7.4+<commit>`; publishes nothing]),
  cmd("lb release check --fast", [the same without the suite and the distributions; no release starts from it]),
  cmd("lb release check stage", [one phase, or several; they always run in their order]),
  cmd("lb release check components bundles --only linux-x86_64", [one builder: narrows `update`, `components`, `bundles`]),
  cmd("lb release status", [where the release has got to: the tree, the run directory, PyPI]),
  cmd("lb release publish 0.8.0", [the checked commit as 0.8.0: the version committed (not pushed), the checked files labelled, the bundles made again, staged, then to PyPI and the CDN and read back. No undo: asks on the terminal unless `--yes`; `0.8.0rc1` is a pre-release]),
  cmd("lb release publish 0.8.0 downloads", [what users download, installed and photographed on the builders]),
)
#table(
  columns: (auto, 1fr),
  stroke: none,
  inset: (x: 0pt, y: 1.4pt),
  column-gutter: 0.6em,
  [*check*], raw("update  components  wheel  label  bundles  stage  distros"),
  [*publish*], raw("release  update  bundles  stage  publish  verify  downloads  tap  docs"),
)
#note[
  *Run directory* `build/out/release/<commit>/`: `pypi/`, `bundles/`, `staged/` with `STAGED.json`. A new commit is a new, empty run: run the phases again. *Don't commit during a run*: it stops after the phase that saw HEAD move.

  *Late Windows build:* `check bundles --only windows-x86_64`, `check stage`, then `publish`; PyPI skips what it has.

  *Logs:* `tmp/remote/<platform>.log`. A builder's job runs detached (`~/.lb/runs/` there); the same phase run again watches it.
]

= Housekeeping
#commands(
  cmd("lb tidy --dry-run", [every build on this machine, with its size; `lb tidy` asks before removing, `--yes` does not]),
  cmd("lb bench --runs 5", [a document to the screen, timed stage by stage; `--idle 20` starts cold]),
  cmd("lb fidelity --runs 2", [the same pages rendered twice and scored; `--ref DIR` against reference PDFs]),
)

= Environment
#table(
  columns: (auto, 1fr),
  stroke: none,
  inset: (x: 0pt, y: 1.4pt),
  column-gutter: 0.6em,
  raw("BUILD_ROOT"), [sources and builds (`--build-root`)],
  raw("MIRROR"), [local clones to fetch from (`--mirror`)],
  raw("V8_BUILD_JOBS"), [V8's parallel jobs; `CORE_BUILD_JOBS` for core's ninja],
  raw("ARCH"), [`amd64` or `arm64` (`--arch`)],
  raw("ENGINE"), [`podman` or `docker`],
  raw("LIBERA_PAYLOAD"), [the payload `libera` and the tests use, instead of the components],
  raw("CDN_TOKEN"), [`publish`'s token for the CDN zone],
)
