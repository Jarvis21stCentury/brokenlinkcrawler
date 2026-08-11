import sqlite3
from pathlib import Path

db_path = Path(__file__).parent / "crawler.db"
conn = sqlite3.connect(db_path, check_same_thread=False)
conn.row_factory = sqlite3.Row
conn.execute("PRAGMA journal_mode=WAL")


def init_db():
    conn.execute("""
        create table if not exists jobs (
            id text primary key,
            root_url text not null,
            status text not null,
            max_pages integer not null,
            max_depth integer not null,
            pages_queued integer default 0,
            pages_crawled integer default 0,
            created_at real not null,
            finished_at real,
            error text
        )
    """)
    conn.execute("""
        create table if not exists pages (
            id integer primary key autoincrement,
            job_id text not null,
            url text not null,
            depth integer not null,
            status_code integer,
            crawled_at real not null
        )
    """)
    conn.execute("""
        create table if not exists links (
            id integer primary key autoincrement,
            job_id text not null,
            source_page text not null,
            target_url text not null,
            is_internal integer not null,
            status_code integer,
            status text not null,
            redirect_chain text not null,
            error_message text,
            checked_at real not null
        )
    """)
    conn.execute("create index if not exists idx_links_job on links(job_id)")
    conn.execute("create index if not exists idx_pages_job on pages(job_id)")
    conn.execute("create index if not exists idx_links_status on links(job_id, status)")
    conn.commit()


def close_db():
    conn.close()
