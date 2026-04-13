from zoom_integration import zoom_mgr
from datetime import datetime, timezone, timedelta

def test_time_filter():
    # Meeting ID was 89732348121
    # Current KST is around 16:30 (07:30 UTC)
    # Morning session was around 09:30 (00:30 UTC)
    
    # Let's see if we correctly filter out morning session participants if we specify a late session
    kst = timezone(timedelta(hours=9))
    
    # Morning session: 4/11 09:30 - 11:30
    start_morning = datetime(2026, 4, 11, 9, 30, tzinfo=kst)
    end_morning = datetime(2026, 4, 11, 11, 30, tzinfo=kst)
    
    # Afternoon session: 4/11 16:00 - 16:30
    start_afternoon = datetime(2026, 4, 11, 16, 0, tzinfo=kst)
    end_afternoon = datetime(2026, 4, 11, 16, 30, tzinfo=kst)
    
    print("--- Testing Time Filter (Afternoon) ---")
    p_afternoon = zoom_mgr.get_meeting_participants("89732348121", start_time=start_afternoon, end_time=end_afternoon)
    print(f"Afternoon participants: {len(p_afternoon)}")
    
    print("\n--- Testing Time Filter (Morning) ---")
    p_morning = zoom_mgr.get_meeting_participants("89732348121", start_time=start_morning, end_time=end_morning)
    print(f"Morning participants: {len(p_morning)}")

if __name__ == "__main__":
    test_time_filter()
