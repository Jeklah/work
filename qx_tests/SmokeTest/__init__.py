"""
The SmokeTest suite provides a fast executing shallow but wide set of tests that are to be regularly executed
on the Qx / QxL to prove that builds of software / firmware are worth running a wider and deeper set of regression 
tests over. If the smoke test suite fails, there is little to no point in running further tests over the tested
release other than to diagnose the discovered faults.

Please note that tests outside of this suite that are decorated with the `@pytest.mark.smoke` marker are also included 
in Smoke Test runs in the Jenkins pipeline. The decision as to whether to write a test in this package or in a 
functional area specific package is a decision made by the developer. In general, parameterised tests may be written 
such that there are Smoke Test and full versions of the same test. An example would be the software upgrade test where 
a smoke test version is defined that checks a very small number of source revisions compared to the full version.

A key goal of the smoke test is to ensure that any serious regressions have as short a life as possible through early
discovery.
"""
