"""
Prompt Generation Module for VianaChat MVP
Generates system prompts with Snowflake schema context for the LLM
"""

import streamlit as st

# Configuration Constants - List of tables to include in the context
TABLES_CONFIG = [
    {
        "name": "VIANA_DEV.PUBLIC.SAMDT_SUMMARY_V1_8_3_UNION_V2_KARL",
        "description": "Summary table for SAMDT analytics. `STATUS` column contains values like 'warm_exit', 'unhandled', 'abandonment', 'balk'. `HOUR_SITE_TZ` is the hour of day."
    },
    {
        "name": "VIANA_DEV.PUBLIC.MANIFEST_V4_SESSION_BACKUP_KARL",
        "description": "Manifest table for V4 sessions. `OVERALL_STATUS` can be 'failed' or 'passed'. Use for failed session counts."
    },
    {
        "name": "VIANA_DEV.PUBLIC.SOS_SERVICE_JOURNEY_FACT",
        "description": "Fact table for SOS journeys. Key metrics: `SERVICE_JOURNEY_DURATION_SECONDS` (do NOT use `SERVICE_DURATION_SECONDS`)."
    },
    {
        "name": "VIANA_DEV.PUBLIC.SAMDT_VEHICLE_JOURNEY_FACT",
        "description": "Fact table for SAMDT Vehicle Journeys. Key columns: `SERVICE_DURATION_SECONDS` (use for 'service time' in this table), `JOURNEY_DURATION_SECONDS`. Contains detailed data on vehicle interactions."
    },
    {
        "name": "VIANA_DEV.PUBLIC.SOS_QUEUE_LENGTH_SIMPLE",
        "description": "Simple table for tracking queue lengths. Key columns: `QUEUE_LENGTH`, `AVG_QUEUE_TIME_SECONDS`, `SITE_NAME`, `HOUR`. Use for 'average queue' questions."
    }
]

# Core SQL Generation Prompt Template
GEN_SQL = """
You are an expert Snowflake SQL analyst assistant. Your role is to help users query data by generating accurate SQL queries based ONLY on the provided schema.

### CRITICAL ANTI-HALLUCINATION RULES:
1. **COLUMN NAMES:** You MUST use the exact column names defined in the "Available Tables Schemas" section below. 
   - **NEVER** use `TOTAL_DURATION` or `DURATION` unless it explicitly appears in the schema.
   - **ALWAYS** check for `DURATION_MS`, `DURATION_SECONDS`, or `ELAPSED_TIME` if asking for duration.
2. **Schema Check:** If you cannot find a column that matches the user's request, do NOT guess. Calculate it from available flags.

### Instructions:
1. **Format:** Always wrap your SQL code in ```sql code blocks.
2. **Search:** Use **fuzzy matching** with `ILIKE` for text searches.
3. **Time Handling & Units:**
   - **Trend / Hour of Day:** If asked for "hour of day" or "by hour", use `EXTRACT(HOUR FROM <timestamp_column>)` and GROUP BY/ORDER BY it. Look for columns like `SITE_TIMESTAMP_UTC`, `SESSION_START_TIME`, or `HOUR_SITE_TZ`.
   - **CONVERSION:** If asked for "Duration" or "Service Time", convert seconds to hours by dividing by 3600 and alias with `_HOURS`.
   - **INDICATORS:** You **MUST** include the unit in your column alias (e.g., `_SECONDS`, `_HOURS`).
4. **Logic & Aggregation:**
   - **Failures:** 
     - In the `MANIFEST` table, "failures" are when `OVERALL_STATUS = 'failed'`.
     - In the `SAMDT_SUMMARY` table, "failures" or "issues" can be identified by `STATUS` values like 'abandonment', 'balk', or 'unhandled'.
     - **ALWAYS** check the specific status values in the table descriptions below.
   - **Aggregation Rule:** Use metrics like `AVG`, `MAX`, or `COUNT`. Use positional grouping (e.g., `GROUP BY 1, 2`).
5. **Limits:** Limit results to 10 rows by default unless it's a trend.

### Available Tables Schemas:
{table_context}

### Guidelines:
- **ALWAYS** include a `GROUP BY 1, 2...` clause if using aggregate functions with other columns.
- **ALWAYS** filter out NULL values for metrics.
- **ALWAYS** label output columns with units.
"""


def get_table_context(table_name: str, table_description: str) -> str:
    """
    Retrieves the schema information for a Snowflake table by querying INFORMATION_SCHEMA.
    
    Args:
        table_name: Fully qualified table name (DATABASE.SCHEMA.TABLE)
        table_description: Human-readable description of the table's purpose
    
    Returns:
        str: Formatted string containing table description and schema details
    """
    try:
        # Split the qualified table name
        parts = table_name.split('.')
        if len(parts) != 3:
            return f"Error: Table name must be in format DATABASE.SCHEMA.TABLE, got: {table_name}"
        
        database, schema, table = parts
        
        # Get Snowflake connection from Streamlit secrets
        conn = st.connection("snowflake")
        
        # Query the INFORMATION_SCHEMA to get column details
        query = f"""
        SELECT 
            COLUMN_NAME,
            DATA_TYPE,
            IS_NULLABLE,
            COLUMN_DEFAULT
        FROM {database}.INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = '{schema}'
            AND TABLE_NAME = '{table}'
        ORDER BY ORDINAL_POSITION;
        """
        
        # Execute query and get results
        columns_df = conn.query(query)
        
        if columns_df.empty:
            return f"Error: No schema information found for table {table_name}"
        
        # Format the schema information
        context = f"#### Table: {table_name}\\n"
        context += f"**Description:** {table_description}\\n\\n"
        context += "**Columns:**\\n"
        
        for _, row in columns_df.iterrows():
            nullable = "NULL" if row['IS_NULLABLE'] == 'YES' else "NOT NULL"
            default = f", DEFAULT: {row['COLUMN_DEFAULT']}" if row['COLUMN_DEFAULT'] else ""
            context += f"  - `{row['COLUMN_NAME']}` ({row['DATA_TYPE']}) - {nullable}{default}\\n"
        
        return context
    
    except Exception as e:
        return f"Error retrieving context for {table_name}: {str(e)}"


def get_system_prompt() -> str:
    """
    Generates the complete system prompt for the LLM, aggregating schemas for all configured tables.
    
    Returns:
        str: Fully formatted system prompt with schema information for all tables
    """
    all_contexts = []
    
    for config in TABLES_CONFIG:
        context = get_table_context(config["name"], config["description"])
        all_contexts.append(context)
    
    combined_context = "\n\n---\n\n".join(all_contexts)
    
    # Insert the context into the prompt template
    return GEN_SQL.format(table_context=combined_context)