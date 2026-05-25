# VianaChat MVP

An AI-powered analytics chatbot that translates natural language questions into SQL queries, executes them on Snowflake, and automatically visualizes the results.

## Features

- **Natural Language to SQL**: Ask questions in plain English, get SQL queries automatically
- **Snowflake Integration**: Direct connection to your Snowflake data warehouse
- **Smart Visualizations**: Automatic chart selection based on data structure
- **Streaming Responses**: Real-time AI responses for better UX
- **Chat History**: Maintains conversation context for follow-up questions

## Prerequisites

- Python 3.8 or higher
- Snowflake account with appropriate access
- OpenAI API key

## Installation

1. **Clone or download this project**

2. **Install dependencies**:

   ```bash
   pip install -r requirements.txt
   ```

3. **Configure secrets**:
   - Navigate to `.streamlit/` folder
   - Copy `secrets.toml.template` to `secrets.toml`
   - Fill in your credentials:
     - OpenAI API key
     - Snowflake connection details

4. **Update table configuration**:
   - Edit `src/prompts.py`
   - Update `QUALIFIED_TABLE_NAME` to your actual table (format: `DATABASE.SCHEMA.TABLE`)
   - Update `TABLE_DESCRIPTION` with context about your data

## Usage

1. **Start the application**:

   ```bash
   streamlit run app.py
   ```

2. **Open your browser** to the URL shown (typically `http://localhost:8501`)

3. **Ask questions** like:
- What is the average queue length per store?
- What is the average speed of service time per store?
- Which store takes longest to serve customers?

## Project Structure

```
viana_chat_mvp/
├── .streamlit/
│   ├── secrets.toml.template  # Template for credentials
│   └── secrets.toml           # Your actual credentials (gitignored)
├── src/
│   ├── __init__.py
│   ├── prompts.py             # System prompt & schema retrieval
│   └── chart_helpers.py       # Auto-visualization logic
├── app.py                     # Main Streamlit application
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Configuration

### Snowflake Connection

The app uses Streamlit's connection feature. Configure in `.streamlit/secrets.toml`:

```toml
[connections.snowflake]
user = "your_username"
password = "your_password"
account = "your_account_locator"
warehouse = "your_warehouse"
database = "your_database"
schema = "your_schema"
role = "your_role"
```

### OpenAI API

Add your OpenAI API key to `.streamlit/secrets.toml`:

```toml
OPENAI_API_KEY = "sk-..."
```

## How It Works

1. **User Input**: You type a natural language question
2. **Context Injection**: The app retrieves your Snowflake table schema
3. **AI Processing**: OpenAI generates appropriate SQL based on your question and schema
4. **Query Execution**: SQL is executed on Snowflake
5. **Visualization**: Results are displayed in a table and automatically visualized
6. **Chat History**: Context is maintained for follow-up questions

## Customization

### Modify System Prompt

Edit `src/prompts.py` to customize how the AI generates SQL:

- Change `GEN_SQL` template for different instructions
- Adjust `TABLE_DESCRIPTION` for better context

### Add Custom Charts

Extend `src/chart_helpers.py` to add more visualization types:

- Scatter plots
- Pie charts
- Custom Plotly charts

## Example Questions

- "What are the total sales by region?"
- "Show me customer growth over time"
- "List the top 5 products by profit margin"
- "What's the average order value this quarter?"
- "Find all transactions above $10,000"

## Important Notes

- **Never commit `secrets.toml`** - it contains sensitive credentials
- **SQL Limits**: Queries are limited to 10 rows by default (configurable in prompt)
- **Token Usage**: Each question consumes OpenAI API tokens
- **Snowflake Costs**: Query execution incurs Snowflake compute costs

## Troubleshooting

### "No schema information found"

- Verify your table name format: `DATABASE.SCHEMA.TABLE`
- Check that your Snowflake user has access to `INFORMATION_SCHEMA`

### "Error executing SQL query"

- Ensure your warehouse is running
- Verify table permissions
- Check SQL syntax in the generated query

### "Error communicating with OpenAI"

- Verify your API key is correct
- Check your OpenAI account has available credits
- Ensure you have internet connectivity

---

**Built using Streamlit, Snowflake, and OpenAI**
