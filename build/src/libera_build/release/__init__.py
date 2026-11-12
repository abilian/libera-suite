"""A release, built and tested on the builders, then published from here:
`lb release check` and `lb release publish`.

plan       the phases, their order, and every refusal, as pure functions
context    what one run is: the checkout, the builders, the phases
precheck   the facts the refusals need, gathered, before anything long
builds     `lb` on several builders at once, each asserted on what it printed
phases     the work: update, components, builders (bundles), here
           (wheel), staging (stage, distros), publishing (publish, verify,
           downloads)
run        the dispatch, in the one order the phases work in
"""
