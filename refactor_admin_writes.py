import codecs
import re

file_path = "e:\\다운로드\\qr_attendance\\admin_app.py"
with codecs.open(file_path, "r", "utf-8-sig") as f:
    text = f.read()

# 1. schedule generation (group creation)
old_schedule_append = """
                        if not new_schedules.empty:
                            df_schedule = get_schedule_df()
                            df_schedule = pd.concat([df_schedule, new_schedules], ignore_index=True)
                            save_csv_safe(df_schedule, SCHEDULE_CSV)
"""
new_schedule_append = """
                        if not new_schedules.empty:
                            for _, r_sched in new_schedules.iterrows():
                                st_dt = f"{r_sched['date']}T{r_sched['start']}:00"
                                en_dt = f"{r_sched['date']}T{r_sched['end']}:00"
                                try:
                                    supabase_mgr.client.table('schedule').insert({
                                        'class_name': r_sched['session'],
                                        'start_time': st_dt,
                                        'end_time': en_dt
                                    }).execute()
                                except Exception as e:
                                    pass
"""
text = text.replace(old_schedule_append.strip('\n'), new_schedule_append.strip('\n'))

# 2. schedule manual delete
old_schedule_delete = """
                    if st.button("🗑️", key=f"del_sched_{idx}", help="삭제", use_container_width=True):
                        df_sched.drop(idx, inplace=True)
                        df_sched.reset_index(drop=True, inplace=True)
                        if save_csv_safe(df_sched, SCHEDULE_CSV):
                            st.success("일정이 삭제되었습니다.")
                            st.rerun()
"""
new_schedule_delete = """
                    if st.button("🗑️", key=f"del_sched_{idx}", help="삭제", use_container_width=True):
                        try:
                            sched_id = row['id']
                            supabase_mgr.client.table('schedule').delete().eq('id', sched_id).execute()
                            st.success("일정이 삭제되었습니다.")
                            import time
                            time.sleep(1)
                            st.rerun()
                        except Exception as e:
                            st.error(f"삭제 오류: {e}")
"""
text = text.replace(old_schedule_delete.strip('\n'), new_schedule_delete.strip('\n'))

# 3. Mobile Camera attendance insert
old_mobile_log = """
                                df_log = get_attendance_df()
                                
                                new_log = pd.DataFrame([attendance_record])
                                df_log = pd.concat([df_log, new_log], ignore_index=True)
                                save_csv_safe(df_log, ATTENDANCE_LOG_CSV)
"""
new_mobile_log = """
                                try:
                                    # Get student_id
                                    student_rec = supabase_mgr.client.table('students').select('id').eq('student_name', student_name).execute()
                                    student_id = student_rec.data[0]['id'] if student_rec.data else None
                                    
                                    # Get schedule_id
                                    class_start_dt_str = datetime.combine(date.today(), class_start_time).isoformat()
                                    sched_rec = supabase_mgr.client.table('schedule').select('id').eq('class_name', row['session']).eq('start_time', class_start_dt_str).execute()
                                    schedule_id = sched_rec.data[0]['id'] if sched_rec.data else None
                                    
                                    if student_id and schedule_id:
                                        supabase_mgr.client.table('attendance').insert({
                                            'student_id': student_id,
                                            'schedule_id': schedule_id,
                                            'check_in_time': attendance_time.isoformat(),
                                            'status': status,
                                            'type': '오프라인'
                                        }).execute()
                                except Exception as e:
                                    logger.error(f"Mobile attendance SB error: {e}")
"""
text = text.replace(old_mobile_log.strip('\n'), new_mobile_log.strip('\n'))

# 4. Editing Attendance
old_attendance_edit = """                                        if mask.any():
                                            df_full.loc[mask, 'status'] = new_status
                                            
                                            if 'date_original' in df_full.columns:
                                                df_full['date'] = df_full['date_original']
                                                df_full = df_full.drop(columns=['date_original'])
                                            
                                            df_full.to_csv(ATTENDANCE_LOG_CSV, index=False, encoding='utf-8-sig')
                                            st.success(f"✅ {record['student_name']}의 상태가 '{new_status}'로 변경되었습니다!")
                                            logger.info(f"Attendance updated: {record['student_name']} -> {new_status}")
                                            import time
                                            time.sleep(1)
                                            st.rerun()
                                        else:
                                            st.error("❌ 레코드를 찾을 수 없습니다.")"""
new_attendance_edit = """                                        try:
                                            # Update directly in Supabase using the record's specific ID if available
                                            # Wait, get_attendance_df provides 'id' from attendance table? We added it!
                                            # record['id'] should exist if we passed it in 'record'
                                            rec_id = record.get('id')
                                            if rec_id:
                                                supabase_mgr.client.table('attendance').update({'status': new_status}).eq('id', rec_id).execute()
                                                st.success(f"✅ 상태가 '{new_status}'로 변경되었습니다!")
                                                import time
                                                time.sleep(1)
                                                st.rerun()
                                            else:
                                                st.error("레코드를 찾을 수 없습니다 (ID 없음).")
                                        except Exception as e:
                                            st.error(f"❌ 수정 실패: {e}")"""
text = text.replace(old_attendance_edit.strip('\n'), new_attendance_edit.strip('\n'))

old_attendance_del = """                                        mask = (df_full['date'] == edit_date) & (df_full['session'] == edit_session) & (df_full['student_name'] == record['student_name'])
                                        df_full = df_full[~mask]
                                        
                                        if 'date_original' in df_full.columns:
                                            df_full['date'] = df_full['date_original']
                                            df_full = df_full.drop(columns=['date_original'])
                                        
                                        df_full.to_csv(ATTENDANCE_LOG_CSV, index=False, encoding='utf-8-sig')"""
new_attendance_del = """                                        rec_id = record.get('id')
                                        if rec_id:
                                            supabase_mgr.client.table('attendance').delete().eq('id', rec_id).execute()
                                        else:
                                            raise Exception("레코드 ID가 없습니다.")"""
text = text.replace(old_attendance_del.strip('\n'), new_attendance_del.strip('\n'))

# 5. Adding attendance log manually
old_attendance_add = """                            df_full = get_attendance_df()
                            
                            column_mapping = {'name': 'student_name', 'student': 'student_name', 'code': 'qr_code', 'time': 'timestamp'}
                            df_full = df_full.rename(columns=column_mapping)
                            
                            new_record = pd.DataFrame([{'date': edit_date.isoformat(), 'session': edit_session, 'student_name': add_student, 'qr_code': add_student, 'timestamp': datetime.combine(edit_date, add_time).strftime('%Y-%m-%d %H:%M:%S'), 'status': add_status}])
                            
                            df_full = pd.concat([df_full, new_record], ignore_index=True)
                            df_full.to_csv(ATTENDANCE_LOG_CSV, index=False, encoding='utf-8-sig')"""
new_attendance_add = """                            student_res = supabase_mgr.client.table('students').select('id').eq('student_name', add_student).execute()
                            student_id = student_res.data[0]['id'] if student_res.data else None
                            
                            # Finding schedule
                            sel_start_dt = str(edit_date) + 'T' + selected_class['start'] + ':00'
                            sched_res = supabase_mgr.client.table('schedule').select('id').eq('class_name', edit_session).eq('start_time', sel_start_dt).execute()
                            schedule_id = sched_res.data[0]['id'] if sched_res.data else None
                            
                            if student_id and schedule_id:
                                supabase_mgr.insert_attendance(
                                    student_id=student_id,
                                    schedule_id=schedule_id,
                                    check_in_time=datetime.combine(edit_date, add_time).isoformat(),
                                    status=add_status,
                                    type_str='오프라인'
                                )"""
text = text.replace(old_attendance_add.strip('\n'), new_attendance_add.strip('\n'))

# 6. Bulk Absences
old_bulk_add = """                            df_full = get_attendance_df()
                            
                            column_mapping = {'name': 'student_name', 'student': 'student_name', 'code': 'qr_code', 'time': 'timestamp'}
                            df_full = df_full.rename(columns=column_mapping)
                            
                            absence_time = datetime.combine(edit_date, datetime.strptime(selected_class['end'], '%H:%M').time())
                            
                            new_records = []
                            for student in missing_students:
                                new_records.append({'date': edit_date.isoformat(), 'session': edit_session, 'student_name': student, 'qr_code': student, 'timestamp': absence_time.strftime('%Y-%m-%d %H:%M:%S'), 'status': ATTENDANCE_STATUS_ABSENT})
                            
                            df_new = pd.DataFrame(new_records)
                            df_full = pd.concat([df_full, df_new], ignore_index=True)
                            df_full.to_csv(ATTENDANCE_LOG_CSV, index=False, encoding='utf-8-sig')"""
new_bulk_add = """                            absence_time = datetime.combine(edit_date, datetime.strptime(selected_class['end'], '%H:%M').time()).isoformat()
                            
                            sel_start_dt = str(edit_date) + 'T' + selected_class['start'] + ':00'
                            sched_res = supabase_mgr.client.table('schedule').select('id').eq('class_name', edit_session).eq('start_time', sel_start_dt).execute()
                            schedule_id = sched_res.data[0]['id'] if sched_res.data else None
                            
                            if schedule_id:
                                # Get student IDs
                                st_res = supabase_mgr.client.table('students').select('id, student_name').in_('student_name', missing_students).execute()
                                name_to_id = {r['student_name']: r['id'] for r in st_res.data}
                                
                                records = []
                                for student in missing_students:
                                    if student in name_to_id:
                                        records.append({
                                            'student_id': name_to_id[student],
                                            'schedule_id': schedule_id,
                                            'check_in_time': absence_time,
                                            'status': ATTENDANCE_STATUS_ABSENT,
                                            'type': '오프라인'
                                        })
                                if records:
                                    supabase_mgr.client.table('attendance').insert(records).execute()"""
text = text.replace(old_bulk_add.strip('\n'), new_bulk_add.strip('\n'))


with codecs.open(file_path, "w", "utf-8-sig") as f:
    f.write(text)
print("Writes refactored.")
