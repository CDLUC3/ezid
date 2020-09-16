# test_docs

- `77913_r7.bdb`: A real (not 99999 / test) minter randomly selected for development and testing of the EZID minter. It is representative of the minter configuration used by the EZID minters (a subset of the configurations that N2T can handle). It's at a state where it has minted a couple of thousand identifiers but is still in the low range available in the initial, unextended format template, {eedk}.

- `77913_r7_last_before_template_extend.bdb`: The `77913/r7` minter at the final step before running out of room in the initial format template {eedk}. The next minting causes the template to be expanded to {eedeedk} and many of the key values in the database to be reset or recalculated.

