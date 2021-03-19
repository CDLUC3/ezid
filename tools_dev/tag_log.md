
# dev-tag-log

Make EZID log files easier to read by adding "tags" to UUIDs and the unique part of minted identifiers.

Tags are on form, `[[[ ID=x C=y ]]]`, where `ID` is a small integer shared by all instances of the same identifier, and `C` is a 1-based decimal counter, describing how many times the identifier has occurred between the start of the log and the current line. The brackets should make the tags easy to spot in the log.

In the context of logging, the tags highlight the only semantically significant information in the identifiers, which is is if they match other identifiers, and if so, how many. E.g., the untagged log lines,

```2020-11-13 00:00:00,479 INFO 3aa6f45a258611ebb0000aaca0e19d37 BEGIN createIdentifier ark:/13030/m57t34vt
2020-11-13 00:00:00,535 INFO 3aa6f45a258611ebb0000aaca0e19d37 END SUCCESS ark:/13030/m5422d58
```

may be tagged as,

```2020-11-13 00:00:00,479 INFO 3aa6f45a258611ebb0000aaca0e19d37[[[ ID=3 C=1 ]]] BEGIN createIdentifier ark:/13030/m57t34vt[[[ ID=89 C=4 ]]]
2020-11-13 00:00:00,535 INFO 3aa6f45a258611ebb0000aaca0e19d37[[[ ID=3 C=2 ]]] END SUCCESS ark:/13030/m5422d58[[[ ID=90 C=1 ]]]
```

For the UUIDs, `ID=3` in both tags show that they're a matching pair. `C=1` shows that the UUID had not occurred earlier in the log, and `C=2` shows that there's a single earlier match. For the ARKs, the tags show that they're not the same identifier, and that the first ARK has occurred 3 times before, while the second is new. 

The additional piece of information, `I` in the identifier tags, is the total number of identifiers minted on that shoulder up to that point.
