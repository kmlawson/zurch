from typing import List, Optional, Tuple

def build_collection_tree_query() -> str:
    """Build the recursive CTE query for collection hierarchy with recursive item counts and library context."""
    return """
    WITH RECURSIVE collection_tree AS (
        SELECT 
            c.collectionID,
            c.collectionName,
            c.parentCollectionID,
            c.libraryID,
            0 as depth,
            c.collectionName as path
        FROM collections c
        WHERE c.parentCollectionID IS NULL
        
        UNION ALL
        
        SELECT 
            c.collectionID,
            c.collectionName,
            c.parentCollectionID,
            c.libraryID,
            ct.depth + 1,
            ct.path || ' > ' || c.collectionName
        FROM collections c
        JOIN collection_tree ct ON c.parentCollectionID = ct.collectionID
    ),
    all_descendants AS (
        SELECT 
            ct1.collectionID as ancestor_id,
            ct2.collectionID as descendant_id
        FROM collection_tree ct1
        JOIN collection_tree ct2 ON (
            ct2.collectionID = ct1.collectionID OR
            ct2.path LIKE ct1.path || ' > %'
        )
    )
    SELECT 
        ct.collectionID,
        ct.collectionName,
        ct.parentCollectionID,
        ct.depth,
        COUNT(DISTINCT ci.itemID) as item_count,
        ct.path,
        ct.libraryID,
        l.type as library_type,
        COALESCE(g.name, 'Personal Library') as library_name
    FROM collection_tree ct
    JOIN libraries l ON ct.libraryID = l.libraryID
    LEFT JOIN groups g ON l.libraryID = g.libraryID
    LEFT JOIN collectionItems ci ON ct.collectionID = ci.collectionID
    GROUP BY ct.collectionID, ct.collectionName, ct.parentCollectionID, ct.depth, ct.path, ct.libraryID, l.type, g.name
    ORDER BY l.type DESC, ct.depth, ct.collectionName
    """

def build_collection_items_query(collection_id: int, only_attachments: bool = False, 
                                after_year: int = None, before_year: int = None, 
                                only_books: bool = False, only_articles: bool = False, 
                                tags: Optional[List[str]] = None) -> Tuple[str, List]:
    """Build query for items in a specific collection with filters and attachment data."""
    # Build date filtering conditions
    date_conditions = []
    query_params = [collection_id]
    
    if after_year is not None:
        date_conditions.append("CAST(SUBSTR(date_data.value, 1, 4) AS INTEGER) >= ?")
        query_params.append(after_year)
    if before_year is not None:
        date_conditions.append("CAST(SUBSTR(date_data.value, 1, 4) AS INTEGER) <= ?")
        query_params.append(before_year)
    
    # Build item type filtering conditions
    type_conditions = []
    if only_books:
        type_conditions.append("it.typeName = 'book'")
    elif only_articles:
        type_conditions.append("it.typeName = 'journalArticle'")
    
    # Add attachment filtering
    attachment_join = ""
    attachment_conditions = []
    if only_attachments:
        attachment_join = "JOIN itemAttachments ia_filter ON (i.itemID = ia_filter.parentItemID OR i.itemID = ia_filter.itemID)"
        attachment_conditions.append("ia_filter.contentType IN ('application/pdf', 'application/epub+zip')")
    
    # Add tag filtering
    tag_conditions = []
    if tags:
        tag_conditions, tag_params = build_tag_conditions(tags)
        query_params.extend(tag_params)

    # Combine all conditions
    where_conditions = ["ci.collectionID = ?"]
    if date_conditions:
        where_conditions.extend(date_conditions)
    if type_conditions:
        where_conditions.extend(type_conditions)
    if attachment_conditions:
        where_conditions.extend(attachment_conditions)
    if tag_conditions:
        where_conditions.extend(tag_conditions)
    
    where_clause = "WHERE " + " AND ".join(where_conditions)
    
    query = f"""
    SELECT 
        i.itemID,
        COALESCE(title_data.value, '') as title,
        it.typeName,
        ci.orderIndex,
        ia.contentType,
        ia.path,
        datetime(i.dateAdded, 'localtime') as dateAdded,
        datetime(i.dateModified, 'localtime') as dateModified
    FROM collectionItems ci
    JOIN items i ON ci.itemID = i.itemID
    JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
    {attachment_join}
    LEFT JOIN (
        SELECT id.itemID, idv.value
        FROM itemData id
        JOIN itemDataValues idv ON id.valueID = idv.valueID
        WHERE id.fieldID = 1  -- title field
    ) title_data ON i.itemID = title_data.itemID
    LEFT JOIN (
        SELECT id.itemID, idv.value
        FROM itemData id
        JOIN itemDataValues idv ON id.valueID = idv.valueID
        WHERE id.fieldID = 6  -- date field (publication date)
    ) date_data ON i.itemID = date_data.itemID
    LEFT JOIN (
        SELECT DISTINCT parentItemID as itemID, contentType, path
        FROM itemAttachments 
        WHERE contentType IN ('application/pdf', 'application/epub+zip', 'text/plain')
        UNION
        SELECT DISTINCT itemID, contentType, path
        FROM itemAttachments 
        WHERE contentType IN ('application/pdf', 'application/epub+zip', 'text/plain')
    ) ia ON i.itemID = ia.itemID
    {where_clause}
    ORDER BY LOWER(COALESCE(title_data.value, ''))
    """
    
    return query, query_params

def build_search_conditions(search_terms, exact_match: bool = False) -> Tuple[List[str], List]:
    """Build search conditions for title or author searches."""
    search_conditions = []
    search_params = []

    if search_terms is None:
        return search_conditions, search_params

    if isinstance(search_terms, list) and len(search_terms) > 1 and not exact_match:
        # Multiple keywords - each must be present (AND logic)
        for keyword in search_terms:
            if '%' in keyword or '_' in keyword:
                # User provided wildcards
                if not keyword.startswith('%'):
                    keyword = '%' + keyword
                if not keyword.endswith('%'):
                    keyword = keyword + '%'
                search_conditions.append("LOWER(idv.value) LIKE LOWER(?)")
                search_params.append(keyword)
            else:
                # Import escape function
                from .utils import escape_sql_like_pattern
                escaped_keyword = escape_sql_like_pattern(keyword)
                search_conditions.append("LOWER(idv.value) LIKE LOWER(?)")
                search_params.append(f"%{escaped_keyword}%")
    else:
        # Single keyword or phrase search
        if isinstance(search_terms, list):
            search_terms = ' '.join(search_terms)
            
        if exact_match:
            search_conditions.append("LOWER(idv.value) = LOWER(?)")
            search_params.append(search_terms)
        else:
            if '%' in search_terms or '_' in search_terms:
                # User provided wildcards
                if not search_terms.startswith('%'):
                    search_terms = '%' + search_terms
                if not search_terms.endswith('%'):
                    search_terms = search_terms + '%'
                search_conditions.append("LOWER(idv.value) LIKE LOWER(?)")
                search_params.append(search_terms)
            else:
                from .utils import escape_sql_like_pattern
                escaped_terms = escape_sql_like_pattern(search_terms)
                search_conditions.append("LOWER(idv.value) LIKE LOWER(?)")
                search_params.append(f"%{escaped_terms}%")

    return search_conditions, search_params


def build_author_search_conditions(author_terms, exact_match: bool = False) -> Tuple[List[str], List]:
    """Build search conditions for author searches."""
    search_conditions = []
    search_params = []
    
    if isinstance(author_terms, list) and len(author_terms) > 1 and not exact_match:
        # Multiple keywords - each must be present in author names (AND logic)
        for keyword in author_terms:
            if '%' in keyword or '_' in keyword:
                # User provided wildcards
                if not keyword.startswith('%'):
                    keyword = '%' + keyword
                if not keyword.endswith('%'):
                    keyword = keyword + '%'
                search_conditions.append("(LOWER(c.firstName) LIKE LOWER(?) OR LOWER(c.lastName) LIKE LOWER(?))")
                search_params.extend([keyword, keyword])
            else:
                from .utils import escape_sql_like_pattern
                escaped_keyword = escape_sql_like_pattern(keyword)
                search_conditions.append("(LOWER(c.firstName) LIKE LOWER(?) OR LOWER(c.lastName) LIKE LOWER(?))")
                search_params.extend([f"%{escaped_keyword}%", f"%{escaped_keyword}%"])
    else:
        # Single keyword or phrase search
        if isinstance(author_terms, list):
            author_terms = ' '.join(author_terms)
            
        if exact_match:
            search_conditions.append("(LOWER(c.firstName) = LOWER(?) OR LOWER(c.lastName) = LOWER(?))")
            search_params.extend([author_terms, author_terms])
        else:
            if '%' in author_terms or '_' in author_terms:
                # User provided wildcards
                if not author_terms.startswith('%'):
                    author_terms = '%' + author_terms
                if not author_terms.endswith('%'):
                    author_terms = author_terms + '%'
                search_conditions.append("(LOWER(c.firstName) LIKE LOWER(?) OR LOWER(c.lastName) LIKE LOWER(?))")
                search_params.extend([author_terms, author_terms])
            else:
                from .utils import escape_sql_like_pattern
                escaped_author = escape_sql_like_pattern(author_terms)
                search_conditions.append("(LOWER(c.firstName) LIKE LOWER(?) OR LOWER(c.lastName) LIKE LOWER(?))")
                search_params.extend([f"%{escaped_author}%", f"%{escaped_author}%"])
    
    return search_conditions, search_params

def build_author_search_conditions(author_terms, exact_match: bool = False) -> Tuple[List[str], List]:
    """Build search conditions for author searches."""
    search_conditions = []
    search_params = []
    
    if isinstance(author_terms, list) and len(author_terms) > 1 and not exact_match:
        # Multiple keywords - each must be present in author names (AND logic)
        for keyword in author_terms:
            if '%' in keyword or '_' in keyword:
                # User provided wildcards
                if not keyword.startswith('%'):
                    keyword = '%' + keyword
                if not keyword.endswith('%'):
                    keyword = keyword + '%'
                search_conditions.append("(LOWER(c.firstName) LIKE LOWER(?) OR LOWER(c.lastName) LIKE LOWER(?))")
                search_params.extend([keyword, keyword])
            else:
                from .utils import escape_sql_like_pattern
                escaped_keyword = escape_sql_like_pattern(keyword)
                search_conditions.append("(LOWER(c.firstName) LIKE LOWER(?) OR LOWER(c.lastName) LIKE LOWER(?))")
                search_params.extend([f"%{escaped_keyword}%", f"%{escaped_keyword}%"])
    else:
        # Single keyword or phrase search
        if isinstance(author_terms, list):
            author_terms = ' '.join(author_terms)
            
        if exact_match:
            search_conditions.append("(LOWER(c.firstName) = LOWER(?) OR LOWER(c.lastName) = LOWER(?))")
            search_params.extend([author_terms, author_terms])
        else:
            if '%' in author_terms or '_' in author_terms:
                # User provided wildcards
                if not author_terms.startswith('%'):
                    author_terms = '%' + author_terms
                if not author_terms.endswith('%'):
                    author_terms = author_terms + '%'
                search_conditions.append("(LOWER(c.firstName) LIKE LOWER(?) OR LOWER(c.lastName) LIKE LOWER(?))")
                search_params.extend([author_terms, author_terms])
            else:
                from .utils import escape_sql_like_pattern
                escaped_author = escape_sql_like_pattern(author_terms)
                search_conditions.append("(LOWER(c.firstName) LIKE LOWER(?) OR LOWER(c.lastName) LIKE LOWER(?))")
                search_params.extend([f"%{escaped_author}%", f"%{escaped_author}%"])
    
    return search_conditions, search_params

def build_tag_conditions(tags: List[str]) -> Tuple[List[str], List]:
    """Build search conditions for tags (AND logic)."""
    tag_conditions = []
    tag_params = []
    
    for i, tag in enumerate(tags):
        tag_conditions.append(f"EXISTS (SELECT 1 FROM itemTags it{i} JOIN tags t{i} ON it{i}.tagID = t{i}.tagID WHERE it{i}.itemID = i.itemID AND LOWER(t{i}.name) = LOWER(?))")
        tag_params.append(tag)
    return tag_conditions, tag_params

def build_name_search_query(name, exact_match: bool = False, only_attachments: bool = False,
                          after_year: int = None, before_year: int = None, 
                          only_books: bool = False, only_articles: bool = False, 
                          tags: Optional[List[str]] = None) -> Tuple[str, str, List]:
    """Build title search query with all filters and attachment data."""
    search_conditions, search_params = build_search_conditions(name, exact_match)
    
    # Add tag filtering
    if tags:
        tag_conditions, tag_params = build_tag_conditions(tags)
        search_conditions.extend(tag_conditions)
        search_params.extend(tag_params)

    where_clause = "WHERE " + " AND ".join(search_conditions)
    
    # Add date filtering if specified
    if after_year is not None:
        where_clause += " AND CAST(SUBSTR(idv_date.value, 1, 4) AS INTEGER) >= ?"
        search_params.append(after_year)
    if before_year is not None:
        where_clause += " AND CAST(SUBSTR(idv_date.value, 1, 4) AS INTEGER) <= ?"
        search_params.append(before_year)
    
    # Add item type filtering if specified
    if only_books:
        where_clause += " AND it.typeName = 'book'"
    elif only_articles:
        where_clause += " AND it.typeName = 'journalArticle'"
    
    # Add attachment filtering if specified
    attachment_join = ""
    if only_attachments:
        attachment_join = """
        JOIN itemAttachments ia_filter ON (i.itemID = ia_filter.parentItemID OR i.itemID = ia_filter.itemID)
        """
        where_clause += " AND ia_filter.contentType IN ('application/pdf', 'application/epub+zip')"
    
    # Count query
    count_query = f"""
    SELECT COUNT(DISTINCT i.itemID)
    FROM items i
    JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
    {attachment_join}
    LEFT JOIN itemData id ON i.itemID = id.itemID AND id.fieldID = 1  -- title field only
    LEFT JOIN itemDataValues idv ON id.valueID = idv.valueID
    LEFT JOIN itemData id_date ON i.itemID = id_date.itemID AND id_date.fieldID = 6  -- date field (publication date)
    LEFT JOIN itemDataValues idv_date ON id_date.valueID = idv_date.valueID
    {where_clause}
    """
    
    # Items query with attachment data
    items_query = f"""
    SELECT DISTINCT
        i.itemID,
        COALESCE(idv.value, '') as title,
        it.typeName,
        ia.contentType,
        ia.path,
        datetime(i.dateAdded, 'localtime') as dateAdded,
        datetime(i.dateModified, 'localtime') as dateModified
    FROM items i
    JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
    {attachment_join}
    LEFT JOIN itemData id ON i.itemID = id.itemID AND id.fieldID = 1  -- title field only
    LEFT JOIN itemDataValues idv ON id.valueID = idv.valueID
    LEFT JOIN itemData id_date ON i.itemID = id_date.itemID AND id_date.fieldID = 6  -- date field (publication date)
    LEFT JOIN itemDataValues idv_date ON id_date.valueID = idv_date.valueID
    LEFT JOIN (
        SELECT DISTINCT parentItemID as itemID, contentType, path
        FROM itemAttachments 
        WHERE contentType IN ('application/pdf', 'application/epub+zip', 'text/plain')
        UNION
        SELECT DISTINCT itemID, contentType, path
        FROM itemAttachments 
        WHERE contentType IN ('application/pdf', 'application/epub+zip', 'text/plain')
    ) ia ON i.itemID = ia.itemID
    {where_clause}
    ORDER BY LOWER(idv.value)
    """
    return count_query, items_query, search_params

def build_author_search_query(author, exact_match: bool = False, only_attachments: bool = False,
                            after_year: int = None, before_year: int = None,
                            only_books: bool = False, only_articles: bool = False, 
                            tags: Optional[List[str]] = None) -> Tuple[str, str, List]:
    """Build author search query with all filters and attachment data."""
    author_conditions, search_params = build_author_search_conditions(author, exact_match)
    
    # Add date filtering if specified
    date_conditions = []
    if after_year is not None:
        date_conditions.append("CAST(SUBSTR(idv_date.value, 1, 4) AS INTEGER) >= ?")
        search_params.append(after_year)
    if before_year is not None:
        date_conditions.append("CAST(SUBSTR(idv_date.value, 1, 4) AS INTEGER) <= ?")
        search_params.append(before_year)
    
    # Add tag filtering
    tag_conditions = []
    if tags:
        tag_conditions, tag_params = build_tag_conditions(tags)
        search_params.extend(tag_params)

    # Combine conditions
    where_conditions = [f"({' AND '.join(author_conditions)})"]
    if date_conditions:
        where_conditions.extend(date_conditions)
    if tag_conditions:
        where_conditions.extend(tag_conditions)
    
    # Add item type filtering if specified
    if only_books:
        where_conditions.append("it.typeName = 'book'")
    elif only_articles:
        where_conditions.append("it.typeName = 'journalArticle'")
    
    # Add attachment filtering if specified
    attachment_join = ""
    if only_attachments:
        attachment_join = """
        JOIN itemAttachments ia_filter ON (i.itemID = ia_filter.parentItemID OR i.itemID = ia_filter.itemID)
        """
        where_conditions.append("ia_filter.contentType IN ('application/pdf', 'application/epub+zip')")
    
    where_clause = "WHERE " + " AND ".join(where_conditions)
    
    # Count query
    count_query = f"""
    SELECT COUNT(DISTINCT i.itemID)
    FROM items i
    JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
    JOIN itemCreators ic ON i.itemID = ic.itemID
    JOIN creators c ON ic.creatorID = c.creatorID
    {attachment_join}
    LEFT JOIN itemData id_date ON i.itemID = id_date.itemID AND id_date.fieldID = 6  -- date field (publication date)
    LEFT JOIN itemDataValues idv_date ON id_date.valueID = idv_date.valueID
    {where_clause}
    """
    
    # Items query with attachment data
    items_query = f"""
    SELECT DISTINCT
        i.itemID,
        COALESCE(idv_title.value, '') as title,
        it.typeName,
        ia.contentType,
        ia.path,
        datetime(i.dateAdded, 'localtime') as dateAdded,
        datetime(i.dateModified, 'localtime') as dateModified
    FROM items i
    JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
    JOIN itemCreators ic ON i.itemID = ic.itemID
    JOIN creators c ON ic.creatorID = c.creatorID
    {attachment_join}
    LEFT JOIN itemData id_title ON i.itemID = id_title.itemID AND id_title.fieldID = 1  -- title field
    LEFT JOIN itemDataValues idv_title ON id_title.valueID = idv_title.valueID
    LEFT JOIN itemData id_date ON i.itemID = id_date.itemID AND id_date.fieldID = 6  -- date field (publication date)
    LEFT JOIN itemDataValues idv_date ON id_date.valueID = idv_date.valueID
    LEFT JOIN (
        SELECT DISTINCT parentItemID as itemID, contentType, path
        FROM itemAttachments 
        WHERE contentType IN ('application/pdf', 'application/epub+zip', 'text/plain')
        UNION
        SELECT DISTINCT itemID, contentType, path
        FROM itemAttachments 
        WHERE contentType IN ('application/pdf', 'application/epub+zip', 'text/plain')
    ) ia ON i.itemID = ia.itemID
    {where_clause}
    ORDER BY LOWER(idv_title.value)
    """
    
    return count_query, items_query, search_params

def build_item_metadata_query() -> str:
    """Build query for item metadata."""
    return """
    SELECT 
        f.fieldName,
        idv.value
    FROM itemData id
    JOIN fields f ON id.fieldID = f.fieldID
    JOIN itemDataValues idv ON id.valueID = idv.valueID
    WHERE id.itemID = ?
    ORDER BY f.fieldName
    """

def build_item_creators_query() -> str:
    """Build query for item creators."""
    return """
    SELECT ct.creatorType, c.firstName, c.lastName
    FROM itemCreators ic
    JOIN creators c ON ic.creatorID = c.creatorID
    JOIN creatorTypes ct ON ic.creatorTypeID = ct.creatorTypeID
    WHERE ic.itemID = ?
    ORDER BY ic.orderIndex
    """

def build_item_collections_query() -> str:
    """Build query for item collections."""
    return """
    WITH RECURSIVE collection_tree AS (
        SELECT 
            collectionID,
            collectionName,
            parentCollectionID,
            0 as depth,
            collectionName as path
        FROM collections 
        WHERE parentCollectionID IS NULL
        
        UNION ALL
        
        SELECT 
            c.collectionID,
            c.collectionName,
            c.parentCollectionID,
            ct.depth + 1,
            ct.path || ' > ' || c.collectionName
        FROM collections c
        JOIN collection_tree ct ON c.parentCollectionID = ct.collectionID
    )
    SELECT ct.path
    FROM collection_tree ct
    JOIN collectionItems ci ON ct.collectionID = ci.collectionID
    WHERE ci.itemID = ?
    ORDER BY ct.path
    """

def build_attachment_query() -> str:
    """Build query for item attachments."""
    return """
    SELECT contentType, path FROM itemAttachments 
    WHERE parentItemID = ? OR itemID = ?
    LIMIT 1
    """

def build_attachment_path_query() -> str:
    """Build query for attachment file paths."""
    return """
    SELECT ia.path, i.key
    FROM itemAttachments ia
    JOIN items i ON ia.itemID = i.itemID
    WHERE ia.parentItemID = ? OR ia.itemID = ?
    LIMIT 1
    """

def build_item_tags_query() -> str:
    """Build query to get tags for a specific item."""
    return """
    SELECT t.name
    FROM itemTags it
    JOIN tags t ON it.tagID = t.tagID
    WHERE it.itemID = ?
    ORDER BY t.name
    """

def build_stats_total_counts_query() -> str:
    """Build query to get total counts of items, collections, and tags."""
    return """
    SELECT 
        (SELECT COUNT(*) FROM items WHERE itemID NOT IN (SELECT itemID FROM itemAttachments)) as total_items,
        (SELECT COUNT(*) FROM collections) as total_collections,
        (SELECT COUNT(*) FROM tags) as total_tags
    """

def build_stats_item_types_query() -> str:
    """Build query to get item counts by type."""
    return """
    SELECT it.typeName, COUNT(i.itemID) as count
    FROM items i
    JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
    WHERE i.itemID NOT IN (SELECT itemID FROM itemAttachments)
    GROUP BY it.typeName
    ORDER BY count DESC
    """

def build_stats_attachment_counts_query() -> str:
    """Build query to get attachment statistics."""
    return """
    SELECT 
        (SELECT COUNT(DISTINCT i.itemID) 
         FROM items i 
         WHERE i.itemID NOT IN (SELECT itemID FROM itemAttachments)
         AND EXISTS (
            SELECT 1 FROM itemAttachments ia 
            WHERE ia.parentItemID = i.itemID 
            AND ia.contentType IN ('application/pdf', 'application/epub+zip')
         )) as items_with_attachments,
        (SELECT COUNT(*) 
         FROM items i 
         WHERE i.itemID NOT IN (SELECT itemID FROM itemAttachments)
         AND NOT EXISTS (
            SELECT 1 FROM itemAttachments ia 
            WHERE ia.parentItemID = i.itemID 
            AND ia.contentType IN ('application/pdf', 'application/epub+zip')
         )) as items_without_attachments
    """

def build_stats_top_tags_query() -> str:
    """Build query to get most frequently used tags."""
    return """
    SELECT t.name, COUNT(it.itemID) as count
    FROM tags t
    JOIN itemTags it ON t.tagID = it.tagID
    JOIN items i ON it.itemID = i.itemID
    WHERE i.itemID NOT IN (SELECT itemID FROM itemAttachments)
    GROUP BY t.name
    ORDER BY count DESC
    LIMIT 40
    """

def build_stats_top_collections_query() -> str:
    """Build query to get collections with most items."""
    return """
    SELECT c.collectionName as name, COUNT(ci.itemID) as count
    FROM collections c
    JOIN collectionItems ci ON c.collectionID = ci.collectionID
    JOIN items i ON ci.itemID = i.itemID
    WHERE i.itemID NOT IN (SELECT itemID FROM itemAttachments)
    GROUP BY c.collectionID, c.collectionName
    ORDER BY count DESC
    LIMIT 20
    """

def build_stats_publication_decades_query() -> str:
    """Build query to get publication counts by decade using actual publication date."""
    return """
    SELECT 
        CASE 
            WHEN idv.value IS NULL OR LENGTH(idv.value) < 4 OR SUBSTR(idv.value, 1, 4) NOT GLOB '[0-9][0-9][0-9][0-9]' THEN 'No Publication Date'
            WHEN CAST(SUBSTR(idv.value, 1, 4) AS INTEGER) < 1900 THEN 'Before 1900'
            WHEN CAST(SUBSTR(idv.value, 1, 4) AS INTEGER) >= 2020 THEN '2020s'
            ELSE 
                CAST((CAST(SUBSTR(idv.value, 1, 4) AS INTEGER) / 10) * 10 AS TEXT) || 's'
        END as decade,
        COUNT(i.itemID) as count
    FROM items i
    LEFT JOIN itemData id_date ON i.itemID = id_date.itemID AND id_date.fieldID = 6
    LEFT JOIN itemDataValues idv ON id_date.valueID = idv.valueID
    WHERE i.itemID NOT IN (SELECT itemID FROM itemAttachments)
    GROUP BY decade
    ORDER BY 
        CASE 
            WHEN decade = 'No Publication Date' THEN 9999
            WHEN decade = 'Before 1900' THEN 0
            WHEN decade = '2020s' THEN 2021
            ELSE CAST(SUBSTR(decade, 1, 4) AS INTEGER)
        END
    """

def build_combined_search_query(name=None, author=None, exact_match: bool = False, 
                               only_attachments: bool = False, after_year: int = None, 
                               before_year: int = None, only_books: bool = False, 
                               only_articles: bool = False, tags: Optional[List[str]] = None) -> Tuple[str, str, List]:
    """Build combined name and author search query with all filters and attachment data."""
    
    # Build conditions
    all_conditions = []
    search_params = []
    
    # Add name search conditions
    if name:
        name_conditions, name_params = build_search_conditions(name, exact_match)
        all_conditions.extend(name_conditions)
        search_params.extend(name_params)
    
    # Add author search conditions
    if author:
        author_conditions, author_params = build_author_search_conditions(author, exact_match)
        all_conditions.extend(author_conditions)
        search_params.extend(author_params)
    
    # Add tag filtering
    if tags:
        tag_conditions, tag_params = build_tag_conditions(tags)
        all_conditions.extend(tag_conditions)
        search_params.extend(tag_params)
    
    # Build WHERE clause
    where_clause = "WHERE " + " AND ".join(all_conditions) if all_conditions else ""
    
    # Add date filtering if specified
    if after_year is not None:
        where_clause += " AND " if where_clause else "WHERE "
        where_clause += "CAST(SUBSTR(idv_date.value, 1, 4) AS INTEGER) >= ?"
        search_params.append(after_year)
    if before_year is not None:
        where_clause += " AND " if where_clause else "WHERE "
        where_clause += "CAST(SUBSTR(idv_date.value, 1, 4) AS INTEGER) <= ?"
        search_params.append(before_year)
    
    # Add type filtering
    if only_books:
        where_clause += " AND " if where_clause else "WHERE "
        where_clause += "i.itemTypeID = (SELECT itemTypeID FROM itemTypes WHERE typeName = 'book')"
    elif only_articles:
        where_clause += " AND " if where_clause else "WHERE "
        where_clause += "i.itemTypeID IN (SELECT itemTypeID FROM itemTypes WHERE typeName IN ('journalArticle', 'article'))"
    
    # Add attachment filtering
    if only_attachments:
        where_clause += " AND " if where_clause else "WHERE "
        where_clause += "ia.itemID IS NOT NULL"
    
    # Build count query
    count_query = f"""
    SELECT COUNT(DISTINCT i.itemID) 
    FROM items i
    LEFT JOIN itemData id ON i.itemID = id.itemID
    LEFT JOIN itemDataValues idv ON id.valueID = idv.valueID AND id.fieldID = 1
    LEFT JOIN itemData id_date ON i.itemID = id_date.itemID AND id_date.fieldID = 6
    LEFT JOIN itemDataValues idv_date ON id_date.valueID = idv_date.valueID
    LEFT JOIN itemCreators ic ON i.itemID = ic.itemID
    LEFT JOIN creators c ON ic.creatorID = c.creatorID
    LEFT JOIN itemAttachments ia ON i.itemID = ia.parentItemID
    {where_clause}
    """
    
    # Build main query
    main_query = f"""
    SELECT DISTINCT 
        i.itemID,
        COALESCE(idv.value, '') as title,
        it.typeName,
        ia.contentType,
        ia.path as attachment_path,
        datetime(i.dateAdded, 'localtime') as dateAdded,
        datetime(i.dateModified, 'localtime') as dateModified
    FROM items i
    LEFT JOIN itemTypes it ON i.itemTypeID = it.itemTypeID
    LEFT JOIN itemData id ON i.itemID = id.itemID
    LEFT JOIN itemDataValues idv ON id.valueID = idv.valueID AND id.fieldID = 1
    LEFT JOIN itemData id_date ON i.itemID = id_date.itemID AND id_date.fieldID = 6
    LEFT JOIN itemDataValues idv_date ON id_date.valueID = idv_date.valueID
    LEFT JOIN itemCreators ic ON i.itemID = ic.itemID
    LEFT JOIN creators c ON ic.creatorID = c.creatorID
    LEFT JOIN itemAttachments ia ON i.itemID = ia.parentItemID
    {where_clause}
    ORDER BY LOWER(COALESCE(idv.value, ''))
    """
    
    return count_query, main_query, search_params