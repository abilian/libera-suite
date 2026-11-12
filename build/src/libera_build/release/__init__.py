"""A release, built on the builders and published from here: `lb release ship`.

plan       the phases, their order, and every refusal, as pure functions
context    what one run is: the checkout, the builders, the phases
precheck   the facts the refusals need, gathered, before anything long
builds     `lb` on several builders at once, each asserted on what it printed
phases     the work: update, builders (build, bundles), components, here
           (wheel), staging (stage), publishing (publish, verify)
ship       the dispatch, in the one order the phases work in
"""
