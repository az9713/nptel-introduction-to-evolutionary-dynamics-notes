# Introduction to Evolutionary Dynamics: local study edition

Independent study notes following Prof. Supreet Saini's NPTEL IIT Bombay
[course](https://nptel.ac.in/courses/127101592) and its
[January 2025 playlist](https://www.youtube.com/playlist?list=PLOzRYVm0a65ckpdcVe8KLbhdWxzwT6x55).

The source collection contains all 60 numbered lectures and the separate
orientation recording. The 20-chapter grouping follows lecture numbers; actual
YouTube playlist positions are retained separately because playlist order is
different. The orientation is included in the source index.

The local edition is complete: 20 topic chapters cover all 60 numbered lectures,
with 120 worked chapter problems and six additional numerical-lab problems.
Independent chapter and whole-book scientific review accepted the final bodies
with zero blocking findings. Python examples and offline desktop/mobile reader
checks passed; their evidence is retained in the package.

All 61 retained source recordings have verified
media hashes and preferred transcripts: 26 retrieved uploader-provided English
tracks and 35 local machine transcriptions. The uploader's “NPTEL Verified”
label does not identify how a subtitle track was produced. Retained media total
108,042.401 seconds; rounded playlist durations are recorded separately.
Scientific review, actual code execution and reader checks are recorded
separately from source acquisition.

[Open the lecture notes](index.html) locally.
Reader-only rebuilds work from this directory with `python tools/build_book.py`.
Run `python tools/validate_books.py --browser` for the reader checks; browser
checks require Python Playwright and an installed supported browser.
The worked numerical example runs with `python numerical_lab.py`. Independent
numerical checks run with `python tools/audit_numerical_lab.py` and additionally
require NumPy and SciPy.
All rendering assets are local. The reader uses the same CSS, JavaScript,
MathJax, guarded-body builder, metadata sidecars, and provenance boundaries as
the Stanford notes workflow.

Each topic chapter includes substantial original explanations, explicit
mathematical assumptions, runnable examples, and six worked problems. The
numerical lab compares exact finite-population fixation, absorption clocks,
growth and frequency dynamics. External papers are cited with the actual
pages or figures inspected; synthetic examples are identified as such.

Automated keyboard/control and responsive-layout checks supplement editorial
review. Human accessibility testing is unperformed; no accessibility
certification is claimed.

Recordings determine topic order and timestamps. Added explanations, numerical
examples, exercises, and primary-source extensions require their own evidence
labels. Raw audio, transcripts, and acquisition logs remain outside the course
repository. No publication has been authorized or performed.

The [source map](source-map.html), [primary references](references.html),
[source validation record](source-validation-summary.json),
[editorial record](editorial-review-summary.json), and
[workflow](WORKFLOW.md) keep evidence and completion checks inspectable.
The [course review](course-review.json), [code checks](chapter-code-validation.json),
[reader checks](reader-validation.json), and [completion record](completion.json)
describe the completed local edition and its limits.
