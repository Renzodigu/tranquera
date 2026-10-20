# ISO/IEC 27001:2022 ↔ NIST CSF 2.0 mapping

Each Annex A control in `src/tranquera/catalogs/iso27001_2022.yaml` lists the NIST CSF 2.0
subcategories it contributes to (`nist:`). The mapping is **indicative**: it was written by the
author from the intent of each control and is not NIST's official informative reference. For formal
work, compare it with the informative references NIST publishes for CSF 2.0.

## How the NIST view is computed

For every CSF 2.0 subcategory Tranquera looks at the in-scope Annex A controls mapped to it:

| Mapped controls | Subcategory status |
| --- | --- |
| all *met* | met |
| all *not met* | not met |
| any other mix | partial |
| none (or all excluded) | not mapped |

Many **Govern** subcategories (risk strategy, risk appetite, oversight) and some **Identify**
subcategories (risk analysis) correspond to the management-system clauses 4 to 10 of ISO/IEC 27001,
not to Annex A. Tranquera does not assess those clauses yet, so they show as *not mapped* rather
than as gaps.

## Copyright

The ISO/IEC 27001 text is copyrighted. The catalog contains only control identifiers and short
titles written in the author's own words. NIST CSF 2.0 is a U.S. Government work; its descriptions
here are short summaries.
