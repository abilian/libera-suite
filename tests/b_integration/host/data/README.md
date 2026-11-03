# Test documents

- `sentence.xlsb`: written by x2t on macOS, one sentence in one cell.
- `SimpleMacro.docm`, `SimpleMacro.xlsm`, `SimpleMacro.pptm`: from [Apache POI](https://poi.apache.org/)'s test data (`test-data/document`, `spreadsheet` and `slideshow`), under the Apache License 2.0. Each carries a small VBA project, `vbaProject.bin`.
- `fdo59530.doc`: from [LibreOffice](https://www.libreoffice.org/)'s test data (`sw/qa/extras/ww8export/data`), under the Mozilla Public License 2.0. A Word 97-2003 document whose text is `aaa bbb ccc`.
- `signed/`: from [Apache POI](https://poi.apache.org/)'s test data (`test-data/xmldsign`), under the Apache License 2.0. OOXML documents with digital signatures, most made by Microsoft Office 2007, 2010 and 2016 (each signature's `OfficeVersion` says which), two by other signers. `test_signatures_libreoffice.py` asks LibreOffice what each signature is worth, and our verifier must agree.
