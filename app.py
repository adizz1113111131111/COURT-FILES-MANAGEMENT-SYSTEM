from flask import Flask, render_template, request, redirect, url_for
import sqlite3

app = Flask(__name__)

# System State Variables
SHOW_DASHBOARD_STATE = True
IS_AUTHORIZED = True  # Hardcoded True for direct hackathon demonstration access
ADMIN_CLEARANCE_TOKEN = "JUDGE-2026-SECURE"

def get_db_connection():
    conn = sqlite3.connect('court.db')
    conn.row_factory = sqlite3.Row
    return conn

@app.route('/')
def home():
    search_word = request.args.get('search_text', '').strip()
    filter_type = request.args.get('case_type', '')
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # 1. Fetching Active Cases with Filters
    query = "SELECT * FROM cases WHERE 1=1"
    parameters = []
    
    if search_word:
        query += " AND (case_name LIKE ? OR case_number LIKE ? OR description LIKE ?)"
        search_param = f"%{search_word}%"
        parameters.extend([search_param, search_param, search_param])
        
    if filter_type:
        query += " AND case_type = ?"
        parameters.append(filter_type)
        
    query += " ORDER BY id DESC"
    
    cursor.execute(query, parameters)
    all_cases = cursor.fetchall()
    
    # 2. Fetching Archived Cases for the Recovery Vault Server
    cursor.execute("SELECT * FROM archive_cases ORDER BY id DESC")
    archived_cases = cursor.fetchall()
    
    # 3. Fetching Distinct Categories for Sidebar Filtering Dropdown
    cursor.execute("SELECT DISTINCT case_type FROM cases")
    categories = [row['case_type'] for row in cursor.fetchall()]
    
    conn.close()
    
    return render_template(
        'home.html', 
        cases=all_cases, 
        archive_cases=archived_cases,  # Properly bound database return parameter
        categories=categories,
        search_text=search_word,
        selected_category=filter_type,
        display_dashboard=SHOW_DASHBOARD_STATE,
        is_authorized=IS_AUTHORIZED
    )

@app.route('/authorize', methods=['POST'])
def authorize():
    global IS_AUTHORIZED
    token_input = request.form.get('clearance_token', '').strip()
    if token_input == ADMIN_CLEARANCE_TOKEN:
        IS_AUTHORIZED = True
    return redirect(url_for('home'))

@app.route('/revoke-clearance')
def revoke_clearance():
    global IS_AUTHORIZED
    IS_AUTHORIZED = False
    return redirect(url_for('home'))

@app.route('/toggle-view')
def toggle_view():
    global SHOW_DASHBOARD_STATE
    SHOW_DASHBOARD_STATE = not SHOW_DASHBOARD_STATE
    return redirect(url_for('home'))

@app.route('/update-status', methods=['POST'])
def update_status():
    if not IS_AUTHORIZED:
        return redirect(url_for('home'))
        
    case_id = request.form.get('case_id')
    new_status = request.form.get('status')
    
    conn = get_db_connection()
    conn.execute('UPDATE cases SET status = ? WHERE id = ?', (new_status, case_id))
    conn.commit()
    conn.close()
    return redirect(url_for('home'))

@app.route('/archive-case', methods=['POST'])
def archive_case():
    if not IS_AUTHORIZED:
        return redirect(url_for('home'))
        
    case_id = request.form.get('case_id')
    conn = get_db_connection()
    
    # Safely pull original data from active tables
    case = conn.execute('SELECT * FROM cases WHERE id = ?', (case_id,)).fetchone()
    if case:
        # Convert sqlite3.Row to pure dictionary items excluding raw auto-increment primary ID keys
        case_data = dict(case)
        del case_data['id']
        
        # Ingest seamlessly into recovery/archive ledger layout structure
        columns = ', '.join(case_data.keys())
        placeholders = ', '.join('?' for _ in case_data)
        insert_query = f'INSERT INTO archive_cases ({columns}) VALUES ({placeholders})'
        
        conn.execute(insert_query, list(case_data.values()))
        conn.execute('DELETE FROM cases WHERE id = ?', (case_id,))
        conn.commit()
        
    conn.close()
    return redirect(url_for('home'))

@app.route('/restore-case', methods=['POST'])
def restore_case():
    if not IS_AUTHORIZED:
        return redirect(url_for('home'))
        
    case_id = request.form.get('case_id')
    conn = get_db_connection()
    
    # Safely pull backup file from target Recovery Tables
    archived_case = conn.execute('SELECT * FROM archive_cases WHERE id = ?', (case_id,)).fetchone()
    if archived_case:
        case_data = dict(archived_case)
        del case_data['id']
        
        columns = ', '.join(case_data.keys())
        placeholders = ', '.join('?' for _ in case_data)
        insert_query = f'INSERT INTO cases ({columns}) VALUES ({placeholders})'
        
        conn.execute(insert_query, list(case_data.values()))
        conn.execute('DELETE FROM archive_cases WHERE id = ?', (case_id,))
        conn.commit()
        
    conn.close()
    return redirect(url_for('home'))

@app.route('/add-case', methods=['POST'])
def add_case():
    if not IS_AUTHORIZED:
        return redirect(url_for('home'))
        
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute('''
            INSERT INTO cases (case_number, case_name, case_type, urgency, status, date_filed, description,
                               bench_division, investigation_bureau, evidence_repo_id, vault_index, legal_sections, next_hearing)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            request.form.get('case_number'),
            request.form.get('case_name'),
            request.form.get('case_type'),
            request.form.get('urgency'),
            request.form.get('status', 'Under Review'),
            request.form.get('date_filed'),
            request.form.get('description'),
            request.form.get('bench_division', 'General Administrative Bench'),
            request.form.get('investigation_bureau', 'Standard Inquest Division'),
            request.form.get('evidence_repo_id', 'EVID-GEN-001'),
            request.form.get('vault_index', 'VAULT-MAIN-01'),
            request.form.get('legal_sections', 'General Code Regulation'),
            request.form.get('next_hearing', 'To Be Scheduled')
        ))
        conn.commit()
    except sqlite3.IntegrityError:
        pass
    finally:
        conn.close()
        
    return redirect(url_for('home'))

if __name__ == '__main__':
    app.run(debug=True)
