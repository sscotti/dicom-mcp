from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
import os
import json
from mwl_handler import create_mwl_file
from dotenv import load_dotenv
from db_utils import insert_mwl_record, get_DB

load_dotenv()

app = FastAPI()

# Create directories if they don't exist
os.makedirs("templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

# Add templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

WORKLIST_DIR = os.environ.get("WORKLIST_DIR", "/worklist")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        conn = get_DB()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.fetchone()
        cursor.close()
        conn.close()
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database connection failed: {str(e)}")

@app.post("/mwl/create_from_json")
async def create_mwl_from_json(request: Request):
    try:
        json_data = await request.json()
        # Generate filename from AccessionNumber or timestamp
        from datetime import datetime
        filename = f"{json_data.get('AccessionNumber', datetime.now().strftime('%Y%m%d%H%M%S'))}.wl"
        output_path = os.path.join(WORKLIST_DIR, filename)
        ds = create_mwl_file(json_data, output_path)
        row_id = insert_mwl_record(json_data, ds)
        return JSONResponse({
            "status": "success",
            "message": f"MWL file created: {filename}",
            "path": output_path,
            "db_row_id": row_id
        })
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request):
    """Main dashboard page"""
    try:
        conn = get_DB()
        cursor = conn.cursor(dictionary=True)
        
        # Get basic stats with safe defaults
        cursor.execute("SELECT COUNT(*) as total FROM mwl")
        result = cursor.fetchone()
        total_mwl = result['total'] if result else 0
        
        cursor.execute("SELECT COUNT(*) as completed FROM mwl WHERE completed = 1")
        result = cursor.fetchone()
        completed_mwl = result['completed'] if result else 0
        
        cursor.execute("SELECT COUNT(*) as pending FROM mwl WHERE completed = 0")
        result = cursor.fetchone()
        pending_mwl = result['pending'] if result else 0
        
        # Check if MPPS table exists
        cursor.execute("SHOW TABLES LIKE 'mpps'")
        has_mpps = cursor.fetchone() is not None
        
        mpps_stats = {"total": 0, "in_progress": 0, "completed": 0}
        if has_mpps:
            cursor.execute("SELECT COUNT(*) as total FROM mpps")
            result = cursor.fetchone()
            mpps_stats['total'] = result['total'] if result else 0
            
            cursor.execute("SELECT COUNT(*) as in_progress FROM mpps WHERE status = 'IN_PROGRESS'")
            result = cursor.fetchone()
            mpps_stats['in_progress'] = result['in_progress'] if result else 0
            
            cursor.execute("SELECT COUNT(*) as completed FROM mpps WHERE status = 'COMPLETED'")
            result = cursor.fetchone()
            mpps_stats['completed'] = result['completed'] if result else 0
        
        cursor.close()
        conn.close()
        
        stats = {
            "mwl": {"total": total_mwl, "completed": completed_mwl, "pending": pending_mwl},
            "mpps": mpps_stats,
            "has_mpps": has_mpps
        }
        
        return templates.TemplateResponse("dashboard.html", {
            "request": request, 
            "stats": stats
        })
        
    except Exception as e:
        return HTMLResponse(f"<h1>Dashboard Error: {str(e)}</h1><p>Try creating some MWL entries first.</p>", status_code=500)

@app.get("/mwl", response_class=HTMLResponse)
async def mwl_list(request: Request):
    """List all MWL entries"""
    try:
        conn = get_DB()
        cursor = conn.cursor(dictionary=True)
        
        # Check if mwl table exists and has the expected columns
        cursor.execute("DESCRIBE mwl")
        columns = cursor.fetchall()
        column_names = [col['Field'] for col in columns]
        
        # Verify required columns exist
        required_columns = ['id', 'AccessionNumber', 'PatientName', 'PatientID', 
                          'ScheduledProcedureStepStartDate', 'ScheduledStationAETitle', 
                          'completed', 'created_at']
        
        missing_columns = [col for col in required_columns if col not in column_names]
        if missing_columns:
            raise Exception(f"Missing columns in mwl table: {', '.join(missing_columns)}")
        
        cursor.execute("""
            SELECT id, AccessionNumber, PatientName, PatientID, 
                   ScheduledProcedureStepStartDate, ScheduledStationAETitle,
                   completed, created_at
            FROM mwl 
            ORDER BY created_at DESC 
            LIMIT 50
        """)
        mwl_entries = cursor.fetchall()
        
        # Handle empty result gracefully
        if not mwl_entries:
            mwl_entries = []
        
        cursor.close()
        conn.close()
        
        return templates.TemplateResponse("mwl_list.html", {
            "request": request,
            "mwl_entries": mwl_entries,
            "empty_message": "No MWL entries found. Create one using the API." if not mwl_entries else None
        })
        
    except Exception as e:
        return HTMLResponse(f"<h1>MWL List Error: {str(e)}</h1><p>Database may not be initialized properly.</p>", status_code=500)

@app.get("/mpps", response_class=HTMLResponse)  
async def mpps_list(request: Request):
    """List all MPPS entries"""
    try:
        conn = get_DB()
        cursor = conn.cursor(dictionary=True)
        
        # Check if MPPS table exists
        cursor.execute("SHOW TABLES LIKE 'mpps'")
        if not cursor.fetchone():
            cursor.close()
            conn.close()
            return HTMLResponse("<h1>MPPS table not found</h1><p>MPPS functionality not available.</p>", status_code=404)
        
        cursor.execute("""
            SELECT id, AccessionNumber, PatientID, status,
                   performed_station_ae_title, started_at, completed_at
            FROM mpps 
            ORDER BY started_at DESC 
            LIMIT 50
        """)
        mpps_entries = cursor.fetchall()
        
        # Handle empty result gracefully
        if not mpps_entries:
            mpps_entries = []
        
        cursor.close()
        conn.close()
        
        return templates.TemplateResponse("mpps_list.html", {
            "request": request,
            "mpps_entries": mpps_entries,
            "empty_message": "No MPPS entries found." if not mpps_entries else None
        })
        
    except Exception as e:
        return HTMLResponse(f"<h1>MPPS List Error: {str(e)}</h1>", status_code=500)