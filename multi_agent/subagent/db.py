import datetime
import os
from sqlalchemy import create_engine, event, TypeDecorator, String, MetaData
from langchain_community.utilities import SQLDatabase

class SQLiteDate(TypeDecorator):
    impl = String
    cache_ok = True

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return datetime.date.fromtimestamp(value / 1000.0)
        if isinstance(value, str):
            try:
                return datetime.date.fromtimestamp(float(value) / 1000.0)
            except ValueError:
                try:
                    return datetime.date.fromisoformat(value)
                except ValueError:
                    return value
        return value

class SQLiteDateTime(TypeDecorator):
    impl = String
    cache_ok = True

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            return datetime.datetime.fromtimestamp(value / 1000.0)
        if isinstance(value, str):
            try:
                return datetime.datetime.fromtimestamp(float(value) / 1000.0)
            except ValueError:
                try:
                    return datetime.datetime.fromisoformat(value)
                except ValueError:
                    return value
        return value

@event.listens_for(MetaData, "column_reflect")
def receive_column_reflect(inspector, table, column_info):
    col_type = column_info.get("type")
    type_name = str(col_type).lower()
    if "date" in type_name:
        column_info["type"] = SQLiteDate()
    elif "timestamp" in type_name or "datetime" in type_name:
        column_info["type"] = SQLiteDateTime()

db_dir = os.path.dirname(os.path.abspath(__file__))
db_path = os.path.join(db_dir, "netflixdb.sqlite")
engine = create_engine(f"sqlite:///{db_path}")
db = SQLDatabase(engine)