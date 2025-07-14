# Zotero Database Field ID Investigation Report

## Issue Identified

During investigation of the Zotero database structure, I discovered that **field ID 14 is incorrectly being used as the publication date field** throughout the codebase. 

## Key Findings

### Field Mapping Verification

Through direct query of the Zotero database `fields` table, I confirmed the complete field mapping:

**Field 6**: `date` (Publication Date)
- Sample values: "1982-00-00 1982", "2004-00-00 2004", "2001-12-18 2001-12-18"
- Usage count: 49,538 entries
- **This is the correct field for publication dates**

**Field 14**: `accessDate` (Access Date)  
- Sample values: "2023-02-01 15:02:14", "2023-02-01 14:59:54", "2021-09-14 09:35:07"
- Usage count: 48,980 entries
- **This is when the item was accessed/downloaded, NOT publication date**

### Impact on Functionality

The incorrect field usage affects:

1. **Date filtering** (`--after`, `--before` flags) - filtering by access date instead of publication date
2. **Statistics** - publication decade analysis using access dates
3. **Search results** - date-based sorting and filtering returning incorrect results

### Files Requiring Updates

The following file contains all instances of incorrect field 14 usage:

**`/Users/kml8/shell/current/zurch/zurch/queries.py`**:
- Line 113: `WHERE id.fieldID = 14  -- date field` (INCORRECT COMMENT)
- Line 328: `LEFT JOIN itemData id_date ON i.itemID = id_date.itemID AND id_date.fieldID = 14  -- date field`
- Line 348: `LEFT JOIN itemData id_date ON i.itemID = id_date.itemID AND id_date.fieldID = 14  -- date field`
- Line 417: `LEFT JOIN itemData id_date ON i.itemID = id_date.itemID AND id_date.fieldID = 14  -- date field`
- Line 439: `LEFT JOIN itemData id_date ON i.itemID = id_date.itemID AND id_date.fieldID = 14  -- date field`
- Line 619: `LEFT JOIN itemData id_date ON i.itemID = id_date.itemID AND id_date.fieldID = 14`
- Line 694: `LEFT JOIN itemData id_date ON i.itemID = id_date.itemID AND id_date.fieldID = 14`
- Line 716: `LEFT JOIN itemData id_date ON i.itemID = id_date.itemID AND id_date.fieldID = 14`

## Complete Field Reference

For future reference, here are the key Zotero field IDs:

```
1   | title
2   | abstractNote  
6   | date          <- PUBLICATION DATE (correct field)
7   | language
8   | shortTitle
14  | accessDate    <- ACCESS DATE (incorrectly used as publication date)
15  | rights
16  | extra
25  | ISBN
37  | publicationTitle
58  | DOI
70  | issue
72  | journalAbbreviation
73  | ISSN
```

## Recommended Fix

**Replace all instances of `fieldID = 14` with `fieldID = 6`** in the queries where date filtering/sorting is intended for publication dates.

Specifically:
1. Change field ID from 14 to 6 in all date-related queries
2. Update comments from "date field" to "publication date field" for clarity
3. Consider if access date functionality is needed separately (field 14)

## Testing Verification

After the fix:
1. Date filtering should work on actual publication years (e.g., 1982, 2004)
2. Statistics should show publication decades correctly  
3. Search results should be ordered by publication date, not access date

This fix will ensure that date-based operations work on the semantically correct publication date rather than the technical access date.