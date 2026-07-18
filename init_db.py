import sqlite3

def init_db():
    conn = sqlite3.connect('court.db')
    cursor = conn.cursor()
    
    # Create Active and Archive tables
    for table_name in ['cases', 'archive_cases']:
        cursor.execute(f'DROP TABLE IF EXISTS {table_name}')
        cursor.execute(f'''
            CREATE TABLE {table_name} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                case_number TEXT NOT NULL,
                case_name TEXT NOT NULL,
                case_type TEXT NOT NULL,
                urgency TEXT NOT NULL,
                status TEXT NOT NULL,
                date_filed TEXT NOT NULL,
                description TEXT,
                bench_division TEXT,
                investigation_bureau TEXT,
                evidence_repo_id TEXT,
                vault_index TEXT,
                legal_sections TEXT,
                next_hearing TEXT
            )
        ''')
    
    conn.commit()
    conn.close()
    print("Dual-server architecture (Active/Archive) initialized.")

if __name__ == '__main__':
    init_db()