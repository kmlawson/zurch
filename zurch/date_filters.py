"""Date filtering utilities for zurch."""

import re
from datetime import datetime, timedelta
from typing import List, Optional, Tuple, Union

import logging

logger = logging.getLogger(__name__)


def parse_relative_date(date_str: str) -> Optional[datetime]:
    """Parse relative date strings like '3 months' or '1 year'.
    
    Args:
        date_str: String like '3m', '6 months', '1y', '2 years'
        
    Returns:
        The calculated date or None if parsing fails
    """
    date_str = date_str.strip().lower()
    
    # Try to match patterns like "3m", "6 months", "1y", "2 years"
    patterns = [
        (r'^(\d+)\s*m(?:onths?)?$', 'months'),
        (r'^(\d+)\s*w(?:eeks?)?$', 'weeks'),
        (r'^(\d+)\s*d(?:ays?)?$', 'days'),
        (r'^(\d+)\s*y(?:ears?)?$', 'years'),
    ]
    
    now = datetime.now()
    
    for pattern, unit in patterns:
        match = re.match(pattern, date_str)
        if match:
            value = int(match.group(1))
            
            if unit == 'days':
                return now - timedelta(days=value)
            elif unit == 'weeks':
                return now - timedelta(weeks=value)
            elif unit == 'months':
                # Approximate months as 30 days
                return now - timedelta(days=value * 30)
            elif unit == 'years':
                # Approximate years as 365 days
                return now - timedelta(days=value * 365)
    
    # Try to parse as absolute date
    try:
        # Try various date formats
        for fmt in ['%Y-%m-%d', '%Y/%m/%d', '%d-%m-%Y', '%d/%m/%Y', '%Y']:
            try:
                return datetime.strptime(date_str, fmt)
            except ValueError:
                continue
    except Exception:
        pass
    
    return None


def parse_date_range(date_str: str) -> Optional[Tuple[datetime, datetime]]:
    """Parse date range strings like '2020-2023' or '2020/01-2023/12'.
    
    Args:
        date_str: String representing a date range
        
    Returns:
        Tuple of (start_date, end_date) or None if parsing fails
    """
    date_str = date_str.strip()
    
    # Try to split by common separators
    separators = [' to ', ' - ', '-', '..', ' .. ']
    
    parts = None
    for sep in separators:
        if sep in date_str:
            parts = date_str.split(sep, 1)
            break
    
    if not parts or len(parts) != 2:
        return None
    
    start_str, end_str = parts[0].strip(), parts[1].strip()
    
    # Parse start and end dates
    start_date = parse_relative_date(start_str)
    end_date = parse_relative_date(end_str)
    
    if start_date and end_date:
        # Ensure start is before end
        if start_date > end_date:
            start_date, end_date = end_date, start_date
        
        # If end date is just a year, make it end of year
        if len(end_str) == 4 and end_str.isdigit():
            end_date = end_date.replace(month=12, day=31, hour=23, minute=59, second=59)
        
        return (start_date, end_date)
    
    return None


def format_date_for_sql(date: datetime) -> str:
    """Format datetime for SQL queries.
    
    Args:
        date: The datetime to format
        
    Returns:
        String formatted for SQL (YYYY-MM-DD)
    """
    return date.strftime('%Y-%m-%d')


def build_date_filter_clause(
    since: Optional[str] = None,
    between: Optional[str] = None,
    after: Optional[int] = None,
    before: Optional[int] = None,
    use_publication_date: bool = True,
    date_field_name: Optional[str] = None
) -> Tuple[str, List[Union[str, int]]]:
    """Build SQL WHERE clause for date filtering.
    
    Args:
        since: Relative date string (e.g., '3m', '1 year')
        between: Date range string (e.g., '2020-2023')
        after: Year to filter after (inclusive)
        before: Year to filter before (inclusive)
        use_publication_date: If True, filter by publication date; if False, by date added
        
    Returns:
        Tuple of (where_clause, params) for SQL query
    """
    clauses = []
    params = []
    
    # Determine which date field to use
    if date_field_name:
        # Use the provided field name
        date_field = date_field_name
    elif use_publication_date:
        date_field = "COALESCE(date_data.value, '')"
    else:
        date_field = "items.dateAdded"
    
    # Handle --since
    if since:
        since_date = parse_relative_date(since)
        if since_date:
            if use_publication_date:
                # For publication date, we need to extract year and compare
                clauses.append(f"CAST(SUBSTR({date_field}, 1, 4) AS INTEGER) >= ?")
                params.append(since_date.year)
            else:
                # For dateAdded, we can use full datetime comparison
                clauses.append(f"{date_field} >= ?")
                params.append(format_date_for_sql(since_date))
    
    # Handle --between
    elif between:  # Use elif because --since and --between are mutually exclusive
        date_range = parse_date_range(between)
        if date_range:
            start_date, end_date = date_range
            if use_publication_date:
                # For publication date, extract year
                clauses.append(f"CAST(SUBSTR({date_field}, 1, 4) AS INTEGER) BETWEEN ? AND ?")
                params.extend([start_date.year, end_date.year])
            else:
                # For dateAdded, use full datetime
                clauses.append(f"{date_field} BETWEEN ? AND ?")
                params.extend([format_date_for_sql(start_date), format_date_for_sql(end_date)])
    
    # Handle --after and --before (if not using --since or --between)
    elif after is not None or before is not None:
        if after is not None:
            clauses.append(f"CAST(SUBSTR({date_field}, 1, 4) AS INTEGER) >= ?")
            params.append(after)
        if before is not None:
            clauses.append(f"CAST(SUBSTR({date_field}, 1, 4) AS INTEGER) < ?")
            params.append(before)
    
    # Join clauses
    where_clause = " AND ".join(clauses) if clauses else ""
    
    return where_clause, params