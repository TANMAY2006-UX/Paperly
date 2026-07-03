import sqlite3
import os
import json

DB_PATH = 'paperly.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.executescript('''
        CREATE TABLE IF NOT EXISTS papers (
            id TEXT PRIMARY KEY,
            title TEXT NOT NULL,
            authors TEXT NOT NULL,
            year INTEGER,
            venue TEXT,
            reading_time_minutes INTEGER,
            json_path TEXT NOT NULL,
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS reading_state (
            user_id TEXT,
            paper_id TEXT,
            last_section_id TEXT,
            bookmarked BOOLEAN,
            PRIMARY KEY (user_id, paper_id)
        );
    ''')
    conn.commit()
    conn.close()

def seed_db():
    init_db()
    conn = get_db()
    cursor = conn.cursor()
    
    # Check if attention-is-all-you-need is already there
    cursor.execute("SELECT id FROM papers WHERE id = 'attention-is-all-you-need'")
    if not cursor.fetchone():
        json_path = 'data/papers/attention-is-all-you-need.json'
        with open(json_path, 'r', encoding='utf-8') as f:
            paper_data = json.load(f)
            
            # Extract total reading time (sum of section estimated reading times + base)
            total_time = sum(section.get('estimated_reading_time', 1) for section in paper_data.get('sections', []))
            
            cursor.execute('''
                INSERT INTO papers (id, title, authors, year, venue, reading_time_minutes, json_path)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                'attention-is-all-you-need',
                paper_data.get('title', 'Attention Is All You Need'),
                json.dumps(paper_data.get('authors', [])),
                2017,
                'NeurIPS',
                total_time,
                json_path
            ))
            
    conn.commit()
    conn.close()

if __name__ == '__main__':
    seed_db()
    print("Database initialized and seeded.")
