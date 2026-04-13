import pandas as pd
import os
from supabase_client import supabase_mgr
from datetime import datetime
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

EXCEL_PATH = r"E:\다운로드\qr_attendance\출석부_최종본_2026-04-11확정.xlsx"
UNMATCHED_CSV = r"E:\다운로드\qr_attendance\unmatched_students.csv"

def sync_excel_to_supabase():
    if not os.path.exists(EXCEL_PATH):
        logger.error(f"Excel file not found at {EXCEL_PATH}")
        return

    # Load all students
    all_students = supabase_mgr.get_all_students()
    student_map = {s['student_name']: s['id'] for s in all_students}
    
    sheets = ['A반', 'B반', 'C반']
    unmatched = []
    sync_count = 0
    
    # Target dates
    schedule_cache = {} # (date, class_name) -> schedule_id
    
    for sheet_name in sheets:
        try:
            logger.info(f"Processing sheet: {sheet_name}")
            df = pd.read_excel(EXCEL_PATH, sheet_name=sheet_name)
            
            # Data starts from index 1 (headers are in row 0)
            for idx, row in df.iterrows():
                name = str(row.iloc[0]).strip() if not pd.isna(row.iloc[0]) else None
                if not name or name == '이름' or name == 'nan' or '합계' in name:
                    continue
                
                # Match student
                student_id = student_map.get(name)
                if not student_id:
                    unmatched.append({
                        'sheet': sheet_name,
                        'original_name': name,
                        'status': 'Not Found in DB'
                    })
                    continue
                
                # Check 4/4 (Col 2) and 4/11 (Col 3)
                for col_idx, target_date in [(2, '2026-04-04'), (3, '2026-04-11')]:
                    status_val = str(row.iloc[col_idx]).strip() if not pd.isna(row.iloc[col_idx]) else ""
                    
                    if "출석" in status_val or "지각" in status_val:
                        final_status = "출석"
                    elif "결석" in status_val:
                        final_status = "결석"
                    else:
                        continue 

                    # Find Schedule ID
                    cache_key = (target_date, sheet_name)
                    if cache_key not in schedule_cache:
                        sched_res = supabase_mgr.client.table('schedule').select('id')\
                            .ilike('class_name', f"{sheet_name}%")\
                            .gte('start_time', f"{target_date}T00:00:00")\
                            .lte('start_time', f"{target_date}T23:59:59")\
                            .execute()
                        if sched_res.data:
                            schedule_cache[cache_key] = sched_res.data[0]['id']
                        else:
                            schedule_cache[cache_key] = None
                    
                    sid = schedule_cache[cache_key]
                    
                    if sid:
                        # Use '오프라인' which is a known valid type
                        att_type = '오프라인'
                        
                        existing = supabase_mgr.client.table('attendance')\
                            .select('id')\
                            .eq('student_id', student_id)\
                            .eq('schedule_id', sid)\
                            .execute()
                        
                        check_in_time = f"{target_date}T10:00:00+09:00"
                        
                        try:
                            if existing.data:
                                supabase_mgr.client.table('attendance').update({
                                    'status': final_status,
                                    'type': att_type
                                }).eq('id', existing.data[0]['id']).execute()
                            else:
                                supabase_mgr.client.table('attendance').insert({
                                    'student_id': student_id,
                                    'schedule_id': sid,
                                    'check_in_time': check_in_time,
                                    'status': final_status,
                                    'type': att_type
                                }).execute()
                            sync_count += 1
                        except Exception as inner_e:
                            logger.error(f"Error for {name} on {target_date}: {inner_e}")

        except Exception as e:
            logger.error(f"Error processing sheet {sheet_name}: {e}")

    # Save unmatched report
    if unmatched:
        df_unmatched = pd.DataFrame(unmatched)
        df_unmatched.to_csv(UNMATCHED_CSV, index=False, encoding='utf-8-sig')
        logger.info(f"Unmatched students saved to {UNMATCHED_CSV}")
    
    print(f"\n[OK] Sync complete: Total {sync_count} records applied.")
    if unmatched:
        print(f"[WARN] Unmatched students: {len(unmatched)} (Check unmatched_students.csv)")

if __name__ == "__main__":
    sync_excel_to_supabase()
