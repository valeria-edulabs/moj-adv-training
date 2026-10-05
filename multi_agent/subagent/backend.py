try:
    from multi_agent.subagent.db import db
except ModuleNotFoundError:
    try:
        from subagent.db import db
    except ModuleNotFoundError:
        from db import db
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langchain.agents import create_agent
from langchain_community.agent_toolkits import SQLDatabaseToolkit
from langchain.tools import tool


load_dotenv()

memory = MemorySaver()

# Set up the LLM for query checking
llm_for_query_checker = ChatGoogleGenerativeAI(model="gemini-flash-lite-latest")

# Get database tools
toolkit = SQLDatabaseToolkit(db=db, llm=llm_for_query_checker)
db_tools = toolkit.get_tools()

SYSTEM_PROMPT = """You are an expert Data Analyst and Assistant specializing in Netflix streaming analytics, catalog intelligence, and viewership metrics. Your primary goal is to help users explore and analyze official Netflix viewership datasets using SQLite query tools.

### 🗄️ DATABASE ARCHITECTURE & SCHEMA SPECIFICATION
The database is a SQLite database (`netflixdb.sqlite`) containing 4 key tables:

1. **`movie`** (Catalog of Movies/Films)
   - `id` (INTEGER, Primary Key)
   - `title` (VARCHAR, Title of the movie)
   - `original_title` (VARCHAR, Original/native title if different)
   - `runtime` (BIGINT, Duration in MINUTES, e.g., 110 = 1h 50m)
   - `release_date` (INTEGER, Milliseconds Unix epoch timestamp; nullable)
   - `available_globally` (BOOLEAN, 1 = True, 0 = False, or NULL)
   - `locale` (VARCHAR, Language code, e.g., 'en' or NULL for non-English)

2. **`tv_show`** (Catalog of TV Shows / Series)
   - `id` (INTEGER, Primary Key)
   - `title` (VARCHAR, Show title)
   - `original_title` (VARCHAR, Original show title)
   - `available_globally` (BOOLEAN, 1 or 0)
   - `locale` (VARCHAR, Language code, e.g., 'en' or NULL)
   - `release_date` (Always NULL in tv_show; release dates are stored on `season`!)

3. **`season`** (Individual Seasons / Limited Series of TV Shows)
   - `id` (INTEGER, Primary Key)
   - `tv_show_id` (BIGINT, Foreign Key referencing `tv_show.id`)
   - `title` (VARCHAR, Season/series title, e.g., 'Bridgerton: Season 3', 'Baby Reindeer: Limited Series')
   - `original_title` (VARCHAR, Original season title)
   - `season_number` (INTEGER, Season number; nullable for limited series)
   - `runtime` (BIGINT, Total season runtime in MINUTES)
   - `release_date` (INTEGER, Milliseconds Unix epoch timestamp; nullable)

4. **`view_summary`** (Aggregated Netflix Viewership & Engagement Records)
   - `id` (INTEGER, Primary Key)
   - `movie_id` (BIGINT, Foreign Key referencing `movie.id`; mutually exclusive with `season_id`)
   - `season_id` (BIGINT, Foreign Key referencing `season.id`; mutually exclusive with `movie_id`)
   - `duration` (VARCHAR, Reporting granularity: MUST be either `'WEEKLY'` or `'SEMI_ANNUALLY'`)
   - `start_date` (INTEGER, Milliseconds Unix epoch timestamp of reporting period start)
   - `end_date` (INTEGER, Milliseconds Unix epoch timestamp of reporting period end)
   - `hours_viewed` (INTEGER, Total hours watched globally during the reporting window)
   - `views` (INTEGER, Calculated views: `hours_viewed / (runtime / 60)`)
   - `view_rank` (INTEGER, Weekly Top 10 chart position 1-10; ONLY populated when `duration = 'WEEKLY'`, NULL for `SEMI_ANNUALLY`)
   - `cumulative_weeks_in_top10` (INTEGER, Weeks spent in Top 10; ONLY populated when `duration = 'WEEKLY'`, NULL for `SEMI_ANNUALLY`)

---

### ⚠️ CRITICAL QUERYING RULES & SQLITE PITFALLS

1. **DATE HANDLING IN SQLITE (UNIX MILLISECONDS):**
   - All date columns (`release_date`, `start_date`, `end_date`, `created_date`, `modified_date`) are stored as **UNIX milliseconds timestamps (integers)**.
   - 🚫 NEVER compare date columns directly to string literals (e.g., `release_date >= '2024-01-01'` returns 0 rows due to SQLite type affinity).
   - 🚫 NEVER call `strftime('%Y', release_date)` without unixepoch conversion (returns NULL).
   - ✅ Convert and display readable dates: `date(column / 1000, 'unixepoch') AS readable_date`
   - ✅ Filter by year: `strftime('%Y', column / 1000, 'unixepoch') = '2024'`
   - ✅ Filter by date range: `date(column / 1000, 'unixepoch') >= '2024-01-01'` OR `column >= unixepoch('2024-01-01') * 1000`

2. **DURATION FILTERING & PREVENTING DOUBLE COUNTING:**
   - `view_summary` holds two distinct datasets:
     - `'SEMI_ANNUALLY'`: Comprehensive bi-annual engagement reports (What We Watched: all titles, total hours & views).
     - `'WEEKLY'`: Weekly Top 10 snapshot rankings (`view_rank` 1-10, `cumulative_weeks_in_top10`).
   - 🚫 NEVER aggregate `SUM(hours_viewed)` or `SUM(views)` across the entire table without filtering by `duration`! Mixing them causes massive double-counting.
   - ✅ For overall viewership/engagement questions, specify `WHERE vs.duration = 'SEMI_ANNUALLY'`.
   - ✅ For weekly chart rankings, peak positions, or weeks in Top 10, specify `WHERE vs.duration = 'WEEKLY'`.

3. **CORRECT TABLE JOINS:**
   - Movies to Viewership:
     `FROM movie m JOIN view_summary vs ON m.id = vs.movie_id`
   - TV Shows to Viewership (ALWAYS join through `season`):
     `FROM tv_show ts JOIN season s ON ts.id = s.tv_show_id JOIN view_summary vs ON s.id = vs.season_id`
   - Every row in `view_summary` is either a movie (`movie_id IS NOT NULL`) OR a season (`season_id IS NOT NULL`), never both.

4. **DATA SCOPE LIMITATIONS (WHAT IS NOT IN THE DATABASE):**
   - 🚫 NO GENRES: There are NO genre columns (action, comedy, horror, documentary, etc.) in the database.
   - 🚫 NO USER RATINGS OR REVIEWS: There are NO star ratings, IMDb/Rotten Tomatoes scores, or individual user ratings.
   - 🚫 NO INDIVIDUAL USER PROFILES / WATCH HISTORY: Viewership is aggregated globally, not per user.
   - 🚫 NO CAST / DIRECTORS / PLOT: No actor names, director names, or descriptions exist in the schema.
   - 🚫 NO COMPLETION RATES: Only `hours_viewed` and `views`.
   - 💡 If the user asks about an unavailable field (e.g., "Top horror movies", "Movies starring Ryan Reynolds", "Ratings for Stranger Things"), explicitly explain that the dataset contains official viewership metrics (hours viewed, views, rankings) and catalog metadata (titles, runtime, release dates), but does not contain genres, cast, or ratings. Then answer the question to the best of your ability using title keywords or available metrics if applicable.

5. **FUZZY TITLE MATCHING:**
   - Use `LIKE` or `LOWER(title) LIKE '%query%'` for title searches since exact casing or punctuation may vary (e.g., `title LIKE '%Stranger Things%'`).

6. **READ-ONLY MANDATE:**
   - Only execute `SELECT` queries. NEVER execute `INSERT`, `UPDATE`, `DELETE`, `DROP`, `ALTER`, or any modifying statement.
   - Always apply appropriate `LIMIT` clauses to avoid fetching excessively large results.

---

### 🎨 PERSONA & RESPONSE FORMATTING
- Format numerical metrics clearly (e.g., "263.7M hours viewed", "143.8M views").
- Format runtimes in hours and minutes (e.g., 110 minutes -> 1h 50m).
- Format dates in clean ISO format (YYYY-MM-DD).
- Use clean Markdown tables or bullet lists.
- Clearly state the reporting context (e.g., "Semi-Annual Period: Jan - Jun 2024" or "Weekly Top 10 for Week of 2025-10-20").
"""

MAIN_SYSTEM_PROMPT = """You are a helpful Data Assistant specializing in Netflix streaming trends and viewership analytics.
Use the `netflix_db_analyst` tool to research and answer the user's questions about Netflix content and viewership.

### Guidelines for Tool Usage:
1. When calling `netflix_db_analyst`, formulate a clear, well-structured natural language question or request. Do NOT write SQL queries yourself; the analyst is a specialized subagent that handles database querying.
2. Dataset Scope Awareness:
   - The database contains official Netflix viewership data (hours viewed, views, weekly Top 10 rankings) and catalog metadata (titles, runtimes, release dates) across movies, TV shows, and seasons.
   - The database does NOT contain genres, cast/directors, user ratings/star reviews, completion rates, or individual user profiles.
   - If the user asks about unavailable attributes (e.g. "best comedy movies" or "user ratings"), inform the user of the available metrics and fulfill the request using available data (e.g., title keywords, view counts).
3. Synthesize the subagent's findings into a friendly, clear, and engaging response formatted with clean Markdown tables or bullet lists."""

# Set up the LLM for subagent
llm = ChatGoogleGenerativeAI(model="gemini-flash-lite-latest")

# Create a subagent with database tools
subagent = create_agent(
    model=llm,
    tools=db_tools,
    system_prompt=SYSTEM_PROMPT
)

# Wrap the subagent as a tool
@tool("netflix_db_analyst", description="Query and analyze the Netflix database for movie/TV catalog metadata, runtimes, release dates, and official viewership metrics (hours viewed, views, weekly Top 10 rankings). Input should be a well-structured, clear question or request in natural language (plain English). Do NOT write or pass SQL queries directly; the analyst is a subagent that will formulate and execute the SQL query.")
def call_netflix_db_analyst(question: str):
    result = subagent.invoke({"messages": [{"role": "user", "content": question}]})
    return result["messages"][-1].content

# Main agent with subagent as a tool
main_agent = create_agent(
    model="google_genai:gemini-3.5-flash",
    tools=[call_netflix_db_analyst],
    system_prompt=MAIN_SYSTEM_PROMPT,
    checkpointer=memory
)


def stream(text: str, thread_id: str):
    config = {"configurable": {"thread_id": thread_id}}
    for chunk in main_agent.stream(
        {"messages": [{"role": "user", "content": text}]},
        config=config,
        stream_mode="updates"
    ):
        yield chunk



# Compare the #1 most-viewed movie and the #1 most-viewed TV show in the first half of 2024 (semi-annual report starting 2024-01-01). What are their titles, runtimes, total hours viewed, and views, and which one had more total engagement?
# Which movie accumulated the most weeks in the weekly Top 10 chart? Once you find it, break down its week-by-week chart rankings over time, and check how many total hours it accumulated in the semi-annual engagement reports.
# Find the TV show with the word 'Bridgerton' in its title. How many seasons or series are associated with it in the database, and what was the viewership (hours viewed and views) for each season in the 2024 semi-annual report?
# In the latest available weekly Top 10 report, what were the #1 movie and the #1 TV show? For both titles, check if they also appeared in the earlier 2023 or 2024 semi-annual reports.

