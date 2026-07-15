import sqlite3
import os
import json
import glob
import math

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
            added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            category TEXT,
            keywords TEXT
        );
        CREATE TABLE IF NOT EXISTS reading_state (
            user_id TEXT,
            paper_id TEXT,
            last_section_id TEXT,
            bookmarked BOOLEAN,
            PRIMARY KEY (user_id, paper_id)
        );
    ''')
    
    # Preserve backward compatibility for existing databases without the new columns
    cursor.execute("PRAGMA table_info(papers)")
    columns = [row[1] for row in cursor.fetchall()]
    if 'category' not in columns:
        cursor.execute("ALTER TABLE papers ADD COLUMN category TEXT")
    if 'keywords' not in columns:
        cursor.execute("ALTER TABLE papers ADD COLUMN keywords TEXT")
        
    conn.commit()
    conn.close()

def seed_db():
    init_db()
    conn = get_db()
    cursor = conn.cursor()
    
    # Automatically discover all JSON files in the data/papers directory
    for json_path in glob.glob(os.path.join('data', 'papers', '*.json')):
        with open(json_path, 'r', encoding='utf-8') as f:
            try:
                paper_data = json.load(f)
            except json.JSONDecodeError:
                print(f"Error parsing {json_path}")
                continue
                
            paper_id = paper_data.get('slug')
            if not paper_id:
                # Fallback to filename without extension and lowercase it for the slug
                paper_id = os.path.splitext(os.path.basename(json_path))[0].lower()
                
            title = paper_data.get('title', 'Unknown Title')
            authors = json.dumps(paper_data.get('authors', []))
            year = paper_data.get('publication_year', paper_data.get('year', 0))
            venue = paper_data.get('venue', '')
            category = paper_data.get('category', 'Uncategorized')
            keywords = json.dumps(paper_data.get('keywords', []))
            
            # Calculate reading time (excluding references and supplementary sections)
            total_time = 0
            for section in paper_data.get('sections', []):
                if section.get('title') == 'References':
                    break
                total_time += section.get('estimated_reading_time', 0)

            # Insert or update
            cursor.execute("SELECT id FROM papers WHERE id = ?", (paper_id,))
            if cursor.fetchone():
                cursor.execute('''
                    UPDATE papers SET
                        title=?, authors=?, year=?, venue=?, reading_time_minutes=?, json_path=?, category=?, keywords=?
                    WHERE id=?
                ''', (title, authors, year, venue, total_time, json_path, category, keywords, paper_id))
            else:
                cursor.execute('''
                    INSERT INTO papers (id, title, authors, year, venue, reading_time_minutes, json_path, category, keywords)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (paper_id, title, authors, year, venue, total_time, json_path, category, keywords))
                
    conn.commit()
    conn.close()

if __name__ == '__main__':
    seed_db()
    print("Database initialized and seeded.")
