# Zotero SQLite Database Structure

## Overview

Zotero uses SQLite as its database backend with a complex Entity-Attribute-Value (EAV) model to handle semi-structured bibliographic data. The database file is named `zotero.sqlite` and is located in the Zotero data directory.

**IMPORTANT**: Database access should be READ-ONLY. Modifying the database can cause corruption, bypass validation, and break sync functionality.

## Core Tables

### Items (`items`)
The central table containing all bibliographic items.

```sql
CREATE TABLE items (
    itemID INTEGER PRIMARY KEY,
    itemTypeID INT NOT NULL,
    dateAdded TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    dateModified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    clientDateModified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    libraryID INT NOT NULL,
    key TEXT NOT NULL,
    version INT NOT NULL DEFAULT 0,
    synced INT NOT NULL DEFAULT 0,
    UNIQUE (libraryID, key),
    FOREIGN KEY (libraryID) REFERENCES libraries(libraryID) ON DELETE CASCADE
);
```

### Collections (`collections`)
Hierarchical organization of items into folders/collections.

```sql
CREATE TABLE collections (
    collectionID INTEGER PRIMARY KEY,
    collectionName TEXT NOT NULL,
    parentCollectionID INT DEFAULT NULL,
    clientDateModified TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    libraryID INT NOT NULL,
    key TEXT NOT NULL,
    version INT NOT NULL DEFAULT 0,
    synced INT NOT NULL DEFAULT 0,
    UNIQUE (libraryID, key),
    FOREIGN KEY (libraryID) REFERENCES libraries(libraryID) ON DELETE CASCADE,
    FOREIGN KEY (parentCollectionID) REFERENCES collections(collectionID) ON DELETE CASCADE
);
```

### Collection Items (`collectionItems`)
Junction table linking items to collections.

```sql
CREATE TABLE collectionItems (
    collectionID INT NOT NULL,
    itemID INT NOT NULL,
    orderIndex INT NOT NULL DEFAULT 0,
    PRIMARY KEY (collectionID, itemID),
    FOREIGN KEY (collectionID) REFERENCES collections(collectionID) ON DELETE CASCADE,
    FOREIGN KEY (itemID) REFERENCES items(itemID) ON DELETE CASCADE
);
```

### Item Data (`itemData` & `itemDataValues`)
EAV model for storing item metadata.

```sql
CREATE TABLE itemData (
    itemID INT,
    fieldID INT,
    valueID,
    PRIMARY KEY (itemID, fieldID),
    FOREIGN KEY (itemID) REFERENCES items(itemID) ON DELETE CASCADE,
    FOREIGN KEY (fieldID) REFERENCES fieldsCombined(fieldID),
    FOREIGN KEY (valueID) REFERENCES itemDataValues(valueID)
);

CREATE TABLE itemDataValues (
    valueID INTEGER PRIMARY KEY,
    value UNIQUE
);
```

### Fields (`fields`)
Defines available metadata fields.

```sql
-- Key metadata fields (fieldID: fieldName):
-- 1: title
-- 2: abstractNote  
-- 6: date (PUBLICATION DATE - use for date filtering)
-- 7: language
-- 8: shortTitle
-- 14: accessDate (ACCESS DATE - when item was downloaded)
-- 15: rights
-- 16: extra
-- 25: ISBN
-- 37: publicationTitle
-- 58: DOI
-- 70: issue
-- 72: journalAbbreviation
-- 73: ISSN

-- IMPORTANT: Field 6 (date) is publication date, Field 14 (accessDate) is access date
-- Use Field 6 for --after/--before date filtering, NOT Field 14
```

### Item Types (`itemTypes`)
Defines types of bibliographic items (book, journalArticle, etc.).

### Item Attachments (`itemAttachments`)
Stores file attachments linked to items.

```sql
CREATE TABLE itemAttachments (
    itemID INTEGER PRIMARY KEY,
    parentItemID INT,
    linkMode INT,
    contentType TEXT,
    charsetID INT,
    path TEXT,
    syncState INT DEFAULT 0,
    storageModTime INT,
    storageHash TEXT,
    lastProcessedModificationTime INT,
    FOREIGN KEY (itemID) REFERENCES items(itemID) ON DELETE CASCADE,
    FOREIGN KEY (parentItemID) REFERENCES items(itemID) ON DELETE CASCADE,
    FOREIGN KEY (charsetID) REFERENCES charsets(charsetID) ON DELETE SET NULL
);
```

## Key Relationships

1. **Items to Collections**: Many-to-many through `collectionItems`
2. **Collections Hierarchy**: Self-referencing through `parentCollectionID`
3. **Item Metadata**: EAV model through `itemData` → `itemDataValues` + `fields`
4. **Attachments**: Linked to parent items through `parentItemID`

## Important Queries

### Get Items with Titles by Collection
```sql
SELECT 
    i.itemID,
    it.typeName,
    idv.value as title
FROM collections c
JOIN collectionItems ci ON c.collectionID = ci.collectionID  
JOIN items i ON ci.itemID = i.itemID
JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
LEFT JOIN itemData id ON i.itemID = id.itemID AND id.fieldID = 1  -- title field
LEFT JOIN itemDataValues idv ON id.valueID = idv.valueID
WHERE c.collectionName = ?
ORDER BY ci.orderIndex;
```

### Get Collection Hierarchy
```sql
WITH RECURSIVE collection_tree AS (
    SELECT collectionID, collectionName, parentCollectionID, 0 as depth
    FROM collections 
    WHERE parentCollectionID IS NULL
    
    UNION ALL
    
    SELECT c.collectionID, c.collectionName, c.parentCollectionID, ct.depth + 1
    FROM collections c
    JOIN collection_tree ct ON c.parentCollectionID = ct.collectionID
)
SELECT * FROM collection_tree ORDER BY depth, collectionName;
```

### Get Items with Attachments
```sql
SELECT 
    i.itemID,
    idv.value as title,
    ia.contentType,
    ia.path,
    CASE 
        WHEN ia.contentType = 'application/pdf' THEN 'pdf'
        WHEN ia.contentType = 'application/epub+zip' THEN 'epub'
        WHEN ia.contentType LIKE 'text/%' THEN 'txt'
        ELSE 'other'
    END as attachment_type
FROM items i
LEFT JOIN itemData id ON i.itemID = id.itemID AND id.fieldID = 1
LEFT JOIN itemDataValues idv ON id.valueID = idv.valueID
LEFT JOIN itemAttachments ia ON i.itemID = ia.parentItemID
WHERE ia.itemID IS NOT NULL;
```

## File Attachments

Attachment files are stored in subdirectories within the Zotero data directory:
- Path format: `storage/{item_key}/filename`
- Key can be found in the `items.key` field
- Actual filename in `itemAttachments.path` (format: `storage:filename`)

## Content Types for Icons

- PDF files: `application/pdf` → Blue book icon 📘
- EPUB files: `application/epub+zip` → Green book icon 📗  
- Text files: `text/*` → Grey document icon 📄

## Database Versioning

The database schema can change between Zotero versions. Always check the `version` table for compatibility:

```sql
SELECT * FROM version;
```

## Security Notes

1. **Read-only access only** - Never modify the database
2. **Lock handling** - Zotero may lock the database while running
3. **Backup considerations** - Always work with copies for testing
4. **Schema changes** - Handle version differences gracefully